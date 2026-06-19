from django.test import SimpleTestCase

from core.template_render import render_template_string


class RenderTemplateStringTests(SimpleTestCase):
    def test_replaces_placeholders(self):
        self.assertEqual(
            render_template_string("Hello {name}", {"name": "Ada"}),
            "Hello Ada",
        )

    def test_missing_placeholder_empty(self):
        self.assertEqual(
            render_template_string("Hello {name}", {}),
            "Hello ",
        )

    def test_none_value_becomes_empty(self):
        self.assertEqual(
            render_template_string("x={y}", {"y": None}),
            "x=",
        )
