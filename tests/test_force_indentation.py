import unittest

from epilint import diagnose, force_format, safe_format


class ForceIndentationTests(unittest.TestCase):
    def format(self, source):
        return force_format(safe_format(source))

    def test_unbraced_if_while_and_for_keep_their_bodies_indented(self):
        source = (
            "int f(int x)\n{\n"
            "    if (x)\n        x++;\n"
            "    while (x < 3)\n        x++;\n"
            "    for (int i = 0; i < 3; i++)\n        x++;\n"
            "    return x;\n}\n"
        )
        self.assertEqual(self.format(source), source)
        self.assertFalse([issue for issue in diagnose(source) if issue.rule == "C-L2"])

    def test_unindented_body_is_indented(self):
        source = "int f(int x)\n{\n    if (x)\n    return 1;\n    return 0;\n}\n"
        expected = "int f(int x)\n{\n    if (x)\n        return 1;\n    return 0;\n}\n"
        self.assertEqual(self.format(source), expected)

    def test_nested_if_else_keeps_existing_indentation(self):
        source = (
            "int f(int a, int b)\n{\n"
            "    if (a)\n        if (b)\n            return 1;\n"
            "        else\n            return 2;\n"
            "    return 0;\n}\n"
        )
        self.assertEqual(self.format(source), source)
        self.assertFalse([issue for issue in diagnose(source) if issue.rule == "C-L2"])

    def test_brace_on_next_line_stays_aligned_with_condition(self):
        source = "int f(int x)\n{\n    if (x)\n    {\n        return 1;\n    }\n    return 0;\n}\n"
        self.assertEqual(self.format(source), source)

    def test_else_if_body_is_indented(self):
        source = (
            "int f(int x)\n{\n"
            "    if (x > 1)\n        return 2;\n"
            "    else if (x)\n        return 1;\n"
            "    else\n        return 0;\n}\n"
        )
        self.assertEqual(self.format(source), source)
        self.assertFalse([issue for issue in diagnose(source) if issue.rule == "C-L2"])


if __name__ == "__main__":
    unittest.main()
