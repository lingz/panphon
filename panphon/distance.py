

import types

import numpy as np
import pkg_resources
import yaml

from . import _panphon
import editdistance


class Distance(_panphon.FeatureTable):
    def __init__(self, feature_set='spe+'):
        filename = _panphon.filenames[feature_set]
        self.segments, self.seg_dict, self.names = self._read_table(filename)
        self.seg_seq = {seg[0]: i for (i, seg) in enumerate(self.segments)}
        self.weights = self._read_weights()
        self.seg_regex = self._build_seg_regex()
        self.longest_seg = max([len(x) for x in list(self.seg_dict.keys())])
        self.dogol_prime = self._dogolpolsky_prime()

    def _dogolpolsky_prime(self, filename='data/dogolpolsky_prime.yml'):
        """Reads Dogolpolsky-prime classes and constructs function cascade."""
        filename = pkg_resources.resource_filename(
            __name__, filename)
        with open(filename, 'r') as f:
            rules = []
            dogol_prime = yaml.load(f.read())
            for rule in dogol_prime:
                rules.append((_panphon.fts(rule['def']), rule['label']))
        return rules

    def map_to_dogol_prime(self, s):
        segs = []
        for seg in self.seg_regex.findall(s):
            fts = self.seg_fts(seg)
            for mask, label in self.dogol_prime:
                if self.match(mask, fts):
                    segs.append(label)
                    break
        return ''.join(segs)

    def feature_difference(self, ft1, ft2):
        """Given two feature values, return the difference.

        ft1, ft2 -- two feature values ('+', '-', or '0')
        """
        if ft1 != ft2:
            if ft1 == '0' or ft2 == '0':
                return 0.5
            else:
                return 1
        else:
            return 0

    def feature_difference_hamming(self, ft1, ft2):
        """Gives the distance between feature values for computing Hamming
        distance. OVERKILL.

        ft1, ft2 -- two feature values ('+', '-', or '0')
        """
        return 0 if ft1 == ft2 else 1

    def levenshtein_distance(self, source, target):
        if len(source) < len(target):
            return self.levenshtein_distance(target, source)
        # So now we have len(source) >= len(target).
        if len(target) == 0:
            return len(source)
        # We call tuple() to force strings to be used as sequences
        # ('c', 'a', 't', 's') - numpy uses them as values by default.
        source = np.array(tuple(source))
        target = np.array(tuple(target))
        # We use a dynamic programming algorithm, but with the
        # added optimization that we only need the last two rows
        # of the matrix.
        previous_row = np.arange(target.size + 1)
        for s in source:
            # Insertion (target grows longer than source):
            current_row = previous_row + 1
            # Substitution or matching:
            # Target and source items are aligned, and either
            # are different (cost of 1), or are the same (cost of 0).
            current_row[1:] = np.minimum(current_row[1:], np.add(previous_row[:-1], target != s))
            # Deletion (target grows shorter than source):
            current_row[1:] = np.minimum(current_row[1:], current_row[0:-1] + 1)
            previous_row = current_row
        return previous_row[-1]

    def fast_levenshtein_distance(self, source, target):
        """Inconvenience wrapper for the distance function in the Levenshtein module."""
        return int(editdistance.eval(source, target))

    def dogol_prime_distance(self, source, target):
        """Approximate Levenshtein distance using phonetic equivalence classes."""
        source = self.map_to_dogol_prime(source)
        target = self.map_to_dogol_prime(target)
        return self.fast_levenshtein_distance(source, target)

    def min_edit_distance(self, del_cost, ins_cost, sub_cost, start, source, target):
        """Return minimum edit distance, parameterized.

        del_cost -- cost function for deletion
        ins_cost -- cost function for insertion
        sub_cost -- cost function for substitution
        start -- start symbol: string for strings, list for
                 list, list of list for list of lists
        source -- source string/sequence of feature vectors
        target -- target string/sequence of feature vectors
        """
        # Get lengths of source and target
        n, m = len(source), len(target)
        source, target = start + source, start + target
        # Create "matrix"
        d = []
        for i in range(n + 1):
            d.append((m + 1) * [None])
        # Initialize "matrix"
        d[0][0] = 0
        for i in range(1, n + 1):
            d[i][0] = d[i - 1][0] + del_cost(source[i])
        for j in range(1, m + 1):
            d[0][j] = d[0][j - 1] + ins_cost(target[j])
        # Recurrence relation
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                d[i][j] = min([
                    d[i - 1][j] + del_cost(source[i]),
                    d[i - 1][j - 1] + sub_cost(source[i], target[j]),
                    d[i][j - 1] + ins_cost(target[j]),
                ])
        return d[n][m]

    def unweighted_deletion_cost(self, v1):
        """Return cost of deleting segment corresponding to feature vector."""
        assert isinstance(v1, list)
        assert isinstance(v1[0], str)
        return sum([0.5 if x == '0' else 1 for x in v1])

    def unweighted_substitution_cost(self, v1, v2):
        """Given two feature vectors, return the difference."""
        assert isinstance(v1, list)
        assert isinstance(v1[0], str)
        diffs = [self.feature_difference(ft1, ft2)
                 for (ft1, ft2) in zip(v1, v2)]
        return sum(diffs)

    def unweighted_insertion_cost(self, v1):
        """Return cost of inserting segment corresponding to feature vector."""
        assert isinstance(v1, list)
        assert isinstance(v1[0], str)
        return sum([0.5 if x == '0' else 1 for x in v1])

    def feature_edit_distance(self, source, target):
        """String edit distance with equally-weighed features.

        All articulatory features are given equal weight. The distance between
        an unspecified value and a specified value is smaller than the distance
        between two features with oppoiste values."""
        return self.min_edit_distance(self.unweighted_deletion_cost,
                                      self.unweighted_insertion_cost,
                                      self.unweighted_substitution_cost,
                                      [[]],
                                      self.word_to_vector_list(source),
                                      self.word_to_vector_list(target))

    def hamming_substitution_cost(self, v1, v2):
        diffs = [self.feature_difference_hamming(ft1, ft2)
                 for (ft1, ft2) in zip(v1, v2)]
        return sum(diffs)

    def hamming_feature_edit_distance(self, source, target):
        """String edit distance with equally-weighed features.

        All articulatory features are given equal weight. The distance between
        an unspecified value and a specified value is smaller than the distance
        between two features with oppoiste values."""
        return self.min_edit_distance(self.unweighted_deletion_cost,
                                      self.unweighted_insertion_cost,
                                      self.hamming_substitution_cost,
                                      [[]],
                                      self.word_to_vector_list(source),
                                      self.word_to_vector_list(target))

    def weighted_feature_difference(self, w, ft1, ft2):
        """Return the weighted difference between two features."""
        return w if ft1 != ft2 else 0

    def weighted_substitution_cost(self, v1, v2):
        """Given two feature vectors, return the difference."""
        assert isinstance(v1, list)
        assert isinstance(v1[0], str)
        diffs = [self.weighted_feature_difference(w, ft1, ft2)
                 for (w, ft1, ft2) in zip(self.weights, v1, v2)]
        return sum(diffs)

    def weighted_insertion_cost(self, v1):
        """Return cost of inserting segment corresponding to feature vector."""
        assert isinstance(v1, list)
        assert isinstance(v1[0], str)
        return sum(self.weights)

    def weighted_deletion_cost(self, v1):
        """Return cost of deleting segment corresponding to feature vector."""
        assert isinstance(v1, list)
        assert isinstance(v1[0], str)
        return sum(self.weights)

    def weighted_feature_edit_distance(self, source, target):
        """String edit distance with weighted features.

        The cost of changine an articulatory feature is weighted according to
        the the class of the feature and the subjective probability of the
        feature changing in phonological alternation and loanword contexts.
        """
        return self.min_edit_distance(self.weighted_deletion_cost,
                                      self.weighted_insertion_cost,
                                      self.weighted_substitution_cost,
                                      [[]],
                                      self.word_to_vector_list(source),
                                      self.word_to_vector_list(target))
