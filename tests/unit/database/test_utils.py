from unittest import TestCase

from pokerserver.database import from_pot_list_string, to_pot_list_string


class TestFromPotListString(TestCase):
    def test_empty_string(self):
        result = from_pot_list_string('')
        self.assertEqual(result, [
            {
                'bets': {}
            }
        ])

    def test_none(self):
        result = from_pot_list_string(None)
        self.assertEqual(result, [
            {
                'bets': {}
            }
        ])

    def test_single_pot(self):
        result = from_pot_list_string('0:10,1:20,2:30')
        self.assertEqual(result, [
            {
                'bets': {
                    0: 10,
                    1: 20,
                    2: 30
                }
            }
        ])

    def test_two_pots_with_empty_second_pot(self):
        result = from_pot_list_string('0:10,1:20,2:30;')
        self.assertEqual(result, [
            {
                'bets': {
                    0: 10,
                    1: 20,
                    2: 30
                }
            }, {
                'bets': {}
            }
        ])

    def test_two_pots(self):
        result = from_pot_list_string('0:10,1:20,2:20;2:10')
        self.assertEqual(result, [
            {
                'bets': {
                    0: 10,
                    1: 20,
                    2: 20
                }
            }, {
                'bets': {
                    2: 10
                }
            }
        ])


class TestToPotListString(TestCase):
    def test_empty_pot(self):
        result = to_pot_list_string([
            {
                'bets': {}
            }
        ])
        self.assertEqual(result, '')

    def test_none(self):
        result = to_pot_list_string(None)
        self.assertEqual(result, '')

    def test_empty_list(self):
        result = to_pot_list_string([])
        self.assertEqual(result, '')

    def test_single_pot(self):
        result = to_pot_list_string([
            {
                'bets': {
                    0: 10,
                    1: 20,
                    2: 30
                }
            }
        ])
        self.assertEqual(result, '0:10,1:20,2:30')

    def test_two_pots_with_empty_second_pot(self):
        result = to_pot_list_string([
            {
                'bets': {
                    0: 10,
                    1: 20,
                    2: 30
                }
            }, {
                'bets': {}
            }
        ])
        self.assertEqual(result, '0:10,1:20,2:30;')

    def test_two_pots(self):
        result = to_pot_list_string([
            {
                'bets': {
                    0: 10,
                    1: 20,
                    2: 20
                }
            }, {
                'bets': {
                    2: 10
                }
            }
        ])
        self.assertEqual(result, '0:10,1:20,2:20;2:10')
