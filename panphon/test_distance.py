#!//usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
from . import distance


class TestLevenshtein(unittest.TestCase):
    def setUp(self):
        self.dist = distance.Distance()

    def test_trivial1(self):
        self.assertEqual(self.dist.levenshtein_distance('pop', 'pʰop'), 1)

    def test_trivial2(self):
        self.assertEqual(self.dist.levenshtein_distance('pop', 'pʰom'), 2)


class TestDogolPrime(unittest.TestCase):
    def setUp(self):
        self.dist = distance.Distance()

    def test_trivial1(self):
        self.assertEqual(self.dist.dogol_prime_distance('pop', 'bob'), 0)

    def test_trivial2(self):
        self.assertEqual(self.dist.dogol_prime_distance('pop', 'bab'), 0)


class TestUnweightedFeatureEditDist(unittest.TestCase):
    def setUp(self):
        self.dist = distance.Distance()

    def test_unweighted_substitution_cost(self):
        self.assertEqual(self.dist.unweighted_substitution_cost(['0', '+', '-'], ['0', '+', '+']), 1)

    def test_unweighted_deletion_cost(self):
        self.assertEqual(self.dist.unweighted_deletion_cost(['+', '-', '+', '0']), 3.5)

    def test_trivial1(self):
        self.assertEqual(self.dist.feature_edit_distance('bim', 'pym'), 3)

    def test_trivial2(self):
        self.assertEqual(self.dist.feature_edit_distance('ti', 'tʰi'), 1)


class TestWeightedFeatureEditDist(unittest.TestCase):
    def setUp(self):
        self.dist = distance.Distance()

    def test_trivial1(self):
        self.assertGreater(self.dist.weighted_feature_edit_distance('ti', 'tʰu'),
                           self.dist.weighted_feature_edit_distance('ti', 'tʰi'))

    def test_trivial2(self):
        self.assertGreater(self.dist.weighted_feature_edit_distance('ti', 'te'),
                           self.dist.weighted_feature_edit_distance('ti', 'tḭ'))
