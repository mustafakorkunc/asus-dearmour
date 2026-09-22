"""
Unit tests for DeArmour GUI Themes & About configuration.
"""

import unittest
from asus_driver_extractor.gui import THEMES, DeArmourGUI


class TestGUIThemes(unittest.TestCase):
    def test_themes_defined(self):
        """Test that all required theme presets are defined."""
        expected_themes = [
            "Catppuccin Mocha",
            "Hacker Mode (Matrix)",
            "Cyberpunk Neon",
            "Nordic Dark",
            "Clean Light",
        ]
        for name in expected_themes:
            self.assertIn(name, THEMES, f"Theme {name} should be present in THEMES")

    def test_theme_color_keys_completeness(self):
        """Test that every theme has the complete set of required color tokens."""
        required_keys = [
            "name",
            "bg_color",
            "card_bg",
            "card_secondary",
            "fg_color",
            "accent_color",
            "btn_bg",
            "btn_hover",
            "btn_fg",
            "btn_accent_bg",
            "btn_accent_fg",
            "success_color",
            "warning_color",
            "text_bg",
            "entry_bg",
            "muted_fg",
            "log_fg",
            "tree_select",
            "border_color",
        ]
        for theme_name, palette in THEMES.items():
            for key in required_keys:
                self.assertIn(key, palette, f"Theme '{theme_name}' missing key '{key}'")
                self.assertTrue(palette[key].startswith("#") or key == "name", f"Key '{key}' in '{theme_name}' should be a hex color")

    def test_hacker_mode_matrix_palette(self):
        """Test that Hacker Mode (Matrix) contains expected neon green color values."""
        matrix = THEMES["Hacker Mode (Matrix)"]
        self.assertEqual(matrix["fg_color"], "#00ff66")
        self.assertEqual(matrix["accent_color"], "#00ff66")
        self.assertEqual(matrix["btn_fg"], "#00ff66")
        self.assertEqual(matrix["text_bg"], "#020502")


if __name__ == "__main__":
    unittest.main()
