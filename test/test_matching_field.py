#!/usr/bin/env python
import unittest
import macaron

class Member(macaron.Model):
    curename = macaron.MatchingField("Cure .+$", max_length=30)

class MatchingFieldTestCase(unittest.TestCase):
    def setUp(self):
        macaron.macaronage(":memory:")
        macaron.create_table(Member)

    def tearDown(self):
        macaron.bake()
        macaron.cleanup()

    def test_basic(self):
        Member.create(curename="Cure Lovely")
        member = Member.get(curename="Cure Lovely")
        self.assertEqual(member.curename, "Cure Lovely")

    def test_invalid(self):
        self.assertRaises(macaron.ValidationError, lambda: Member.create(curename="Milkey Rose"))

if __name__ == "__main__":
    unittest.main()

