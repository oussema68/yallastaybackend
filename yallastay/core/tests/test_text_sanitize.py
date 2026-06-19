from django.test import SimpleTestCase

from core.text_sanitize import sanitize_plain_text


class SanitizePlainTextTests(SimpleTestCase):
    def test_strips_tags(self):
        self.assertEqual(sanitize_plain_text("<b>hi</b>"), "hi")
        self.assertEqual(
            sanitize_plain_text("<script>alert(1)</script>ok"), "alert(1)ok"
        )

    def test_plain_ampersand_and_brackets_preserved(self):
        self.assertEqual(sanitize_plain_text("hello & world"), "hello & world")
        self.assertEqual(sanitize_plain_text("<3"), "<3")

    def test_empty(self):
        self.assertEqual(sanitize_plain_text(""), "")
        self.assertEqual(sanitize_plain_text(None), "")
