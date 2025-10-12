"""Unit tests for utils.translations module."""

import pytest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch, mock_open
from utils.translations import TranslationManager, get_translation_manager, t, TRANSLATIONS


@pytest.fixture
def reset_translation_manager():
    """Reset TranslationManager singleton between tests."""
    # Save original state
    original_instance = TranslationManager._instance
    original_initialized = TranslationManager._initialized

    # Reset singleton
    TranslationManager._instance = None
    TranslationManager._initialized = False

    yield

    # Restore original state
    TranslationManager._instance = original_instance
    TranslationManager._initialized = original_initialized


@pytest.fixture
def temp_settings_dir(tmp_path):
    """Create temporary ~/.gitvys/ directory for testing."""
    settings_dir = tmp_path / ".gitvys"
    settings_dir.mkdir()

    # Mock os.path.expanduser to return temp directory
    with patch('os.path.expanduser') as mock_expand:
        mock_expand.return_value = str(tmp_path)
        yield settings_dir


class TestTranslationManagerSingleton:
    """Tests for TranslationManager singleton pattern."""

    def test_singleton_returns_same_instance(self, reset_translation_manager):
        """Test that TranslationManager returns the same instance."""
        manager1 = TranslationManager()
        manager2 = TranslationManager()

        assert manager1 is manager2

    def test_get_translation_manager_returns_singleton(self, reset_translation_manager):
        """Test that get_translation_manager() returns singleton instance."""
        manager1 = get_translation_manager()
        manager2 = get_translation_manager()

        assert manager1 is manager2
        assert isinstance(manager1, TranslationManager)

    def test_singleton_initialized_once(self, reset_translation_manager):
        """Test that singleton is only initialized once."""
        with patch.object(TranslationManager, '_load_language_preference') as mock_load:
            manager1 = TranslationManager()
            manager2 = TranslationManager()

            # _load_language_preference should only be called once
            assert mock_load.call_count == 1


class TestTranslationManagerInitialization:
    """Tests for TranslationManager initialization."""

    def test_initialization_defaults_to_czech(self, reset_translation_manager):
        """Test that TranslationManager initializes with Czech by default."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            assert manager._current_language == 'cs'

    def test_initialization_loads_language_preference(self, reset_translation_manager):
        """Test that initialization loads language preference from file."""
        with patch.object(TranslationManager, '_load_language_preference') as mock_load:
            manager = TranslationManager()

            mock_load.assert_called_once()

    def test_initialization_creates_empty_callback_list(self, reset_translation_manager):
        """Test that initialization creates empty callback list."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            assert manager._callbacks == []


class TestLanguageGetterSetter:
    """Tests for language getter/setter methods."""

    def test_get_current_language_returns_czech_by_default(self, reset_translation_manager):
        """Test that get_current_language returns 'cs' by default."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            assert manager.get_current_language() == 'cs'

    def test_set_language_changes_current_language(self, reset_translation_manager):
        """Test that set_language changes current language."""
        with patch.object(TranslationManager, '_load_language_preference'):
            with patch.object(TranslationManager, '_save_language_preference'):
                manager = TranslationManager()

                manager.set_language('en')

                assert manager.get_current_language() == 'en'

    def test_set_language_saves_preference(self, reset_translation_manager):
        """Test that set_language saves preference to file."""
        with patch.object(TranslationManager, '_load_language_preference'):
            with patch.object(TranslationManager, '_save_language_preference') as mock_save:
                manager = TranslationManager()

                manager.set_language('en')

                mock_save.assert_called_once()

    def test_set_language_rejects_invalid_language(self, reset_translation_manager):
        """Test that set_language rejects invalid language codes."""
        with patch.object(TranslationManager, '_load_language_preference'):
            with patch.object(TranslationManager, '_save_language_preference') as mock_save:
                manager = TranslationManager()
                original_language = manager.get_current_language()

                manager.set_language('fr')  # French not supported

                # Language should not change
                assert manager.get_current_language() == original_language
                # Save should not be called
                mock_save.assert_not_called()


class TestLanguagePersistence:
    """Tests for language persistence to settings file."""

    def test_load_language_from_existing_settings_file(self, reset_translation_manager, temp_settings_dir):
        """Test loading language from existing settings.json."""
        settings_file = temp_settings_dir / "settings.json"
        settings_file.write_text(json.dumps({'language': 'en', 'theme': 'dark'}))

        manager = TranslationManager()

        assert manager.get_current_language() == 'en'

    def test_load_language_defaults_to_czech_if_file_missing(self, reset_translation_manager, temp_settings_dir):
        """Test that language defaults to Czech if settings.json doesn't exist."""
        # Don't create settings.json
        manager = TranslationManager()

        assert manager.get_current_language() == 'cs'

    def test_load_language_handles_corrupt_settings_file(self, reset_translation_manager, temp_settings_dir):
        """Test that corrupt settings.json is handled gracefully."""
        settings_file = temp_settings_dir / "settings.json"
        settings_file.write_text("{ invalid json }")

        manager = TranslationManager()

        # Should default to Czech on error
        assert manager.get_current_language() == 'cs'

    def test_save_language_creates_settings_file(self, reset_translation_manager, temp_settings_dir):
        """Test that save_language_preference creates settings.json."""
        manager = TranslationManager()
        manager.set_language('en')

        settings_file = temp_settings_dir / "settings.json"
        assert settings_file.exists()

        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            assert settings['language'] == 'en'

    def test_save_language_preserves_other_settings(self, reset_translation_manager, temp_settings_dir):
        """Test that saving language preserves other settings in file."""
        settings_file = temp_settings_dir / "settings.json"
        settings_file.write_text(json.dumps({'language': 'cs', 'theme': 'dark', 'custom': 'value'}))

        manager = TranslationManager()
        manager.set_language('en')

        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            assert settings['language'] == 'en'
            assert settings['theme'] == 'dark'  # Preserved
            assert settings['custom'] == 'value'  # Preserved


class TestTranslationRetrieval:
    """Tests for translation key lookup."""

    def test_get_returns_czech_translation(self, reset_translation_manager):
        """Test that get() returns Czech translation by default."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            translation = manager.get('app_title')

            assert translation == TRANSLATIONS['cs']['app_title']
            assert 'Git Visualizer' in translation

    def test_get_returns_english_translation(self, reset_translation_manager):
        """Test that get() returns English translation after language change."""
        with patch.object(TranslationManager, '_load_language_preference'):
            with patch.object(TranslationManager, '_save_language_preference'):
                manager = TranslationManager()
                manager.set_language('en')

                translation = manager.get('fetch_remote')

                assert translation == TRANSLATIONS['en']['fetch_remote']
                assert translation == 'Fetch remote'

    def test_get_returns_key_for_missing_translation(self, reset_translation_manager):
        """Test that get() returns key for missing translations."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            translation = manager.get('nonexistent_key')

            # Should return key itself as fallback
            assert translation == 'nonexistent_key'

    def test_get_with_format_arguments(self, reset_translation_manager):
        """Test that get() applies format arguments."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            # 'loaded_commits': 'Načteno {} commitů'
            translation = manager.get('loaded_commits', 42)

            assert '42' in translation
            assert 'Načteno' in translation

    def test_get_with_multiple_format_arguments(self, reset_translation_manager):
        """Test that get() handles multiple format arguments."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            # 'tags_format': '{}+{} tagů'
            translation = manager.get('tags_format', 3, 2)

            assert '3' in translation
            assert '2' in translation
            assert '+' in translation

    def test_get_handles_format_error_gracefully(self, reset_translation_manager):
        """Test that get() handles format errors gracefully."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            # Should not raise exception, returns key
            translation = manager.get('loaded_commits')  # Missing format arg

            # Since format fails, should return key
            assert 'loaded_commits' in translation or 'Načteno' in translation


class TestPluralForms:
    """Tests for Czech and English pluralization."""

    @pytest.mark.parametrize("count,expected_form,expected_value,description", [
        (1, 'author_1', 'autor', "Czech: count=1 → singular"),
        (2, 'author_2_4', 'autoři', "Czech: count=2 → special plural (2-4)"),
        (3, 'author_2_4', 'autoři', "Czech: count=3 → special plural (2-4)"),
        (4, 'author_2_4', 'autoři', "Czech: count=4 → special plural (2-4)"),
        (0, 'author_5', 'autorů', "Czech: count=0 → genitive plural"),
        (5, 'author_5', 'autorů', "Czech: count=5 → genitive plural"),
        (10, 'author_5', 'autorů', "Czech: count=10 → genitive plural"),
        (100, 'author_5', 'autorů', "Czech: count=100 → genitive plural"),
    ])
    def test_czech_plural_forms(self, count, expected_form, expected_value, description, reset_translation_manager):
        """Test Czech plural forms (3 forms: 1, 2-4, 0/5+).

        Czech has complex pluralization:
        - 1: singular (autor)
        - 2-4: special plural (autoři)
        - 0, 5+: genitive plural (autorů)
        """
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()
            manager._current_language = 'cs'

            plural = manager.get_plural(count, 'author')

            assert plural == TRANSLATIONS['cs'][expected_form], f"Failed for {description}"
            assert plural == expected_value, f"Failed for {description}"

    @pytest.mark.parametrize("count,expected_form,expected_value,description", [
        (1, 'branch_1', 'branch', "English: count=1 → singular"),
        (0, 'branch_5', 'branches', "English: count=0 → plural"),
        (2, 'branch_5', 'branches', "English: count=2 → plural"),
        (3, 'branch_5', 'branches', "English: count=3 → plural"),
        (10, 'branch_5', 'branches', "English: count=10 → plural"),
    ])
    def test_english_plural_forms(self, count, expected_form, expected_value, description, reset_translation_manager):
        """Test English plural forms (2 forms: 1, other).

        English has simple pluralization:
        - 1: singular (branch)
        - 0, 2+: plural (branches)
        """
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()
            manager._current_language = 'en'

            plural = manager.get_plural(count, 'branch')

            assert plural == TRANSLATIONS['en'][expected_form], f"Failed for {description}"
            assert plural == expected_value, f"Failed for {description}"

    def test_plural_forms_for_all_bases(self, reset_translation_manager):
        """Test that plural forms work for all base keys."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            bases = ['author', 'branch', 'commit', 'tag']

            for base in bases:
                # Should not raise exception for any base
                cs_singular = manager.get_plural(1, base)
                cs_plural = manager.get_plural(5, base)

                assert cs_singular != ''
                assert cs_plural != ''


class TestCallbackSystem:
    """Tests for language change callback system."""

    def test_register_callback_adds_callback(self, reset_translation_manager):
        """Test that register_callback adds callback to list."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()
            callback = MagicMock()

            manager.register_callback(callback)

            assert callback in manager._callbacks

    def test_register_callback_prevents_duplicates(self, reset_translation_manager):
        """Test that register_callback prevents duplicate callbacks."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()
            callback = MagicMock()

            manager.register_callback(callback)
            manager.register_callback(callback)

            # Callback should only be added once
            assert manager._callbacks.count(callback) == 1

    def test_unregister_callback_removes_callback(self, reset_translation_manager):
        """Test that unregister_callback removes callback from list."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()
            callback = MagicMock()

            manager.register_callback(callback)
            manager.unregister_callback(callback)

            assert callback not in manager._callbacks

    def test_set_language_notifies_callbacks(self, reset_translation_manager):
        """Test that set_language notifies all registered callbacks."""
        with patch.object(TranslationManager, '_load_language_preference'):
            with patch.object(TranslationManager, '_save_language_preference'):
                manager = TranslationManager()
                callback1 = MagicMock()
                callback2 = MagicMock()

                manager.register_callback(callback1)
                manager.register_callback(callback2)

                manager.set_language('en')

                callback1.assert_called_once_with('en')
                callback2.assert_called_once_with('en')

    def test_set_language_handles_callback_errors_gracefully(self, reset_translation_manager):
        """Test that callback errors don't break language switching."""
        with patch.object(TranslationManager, '_load_language_preference'):
            with patch.object(TranslationManager, '_save_language_preference'):
                manager = TranslationManager()
                failing_callback = MagicMock(side_effect=Exception("Callback error"))
                success_callback = MagicMock()

                manager.register_callback(failing_callback)
                manager.register_callback(success_callback)

                # Should not raise exception
                manager.set_language('en')

                # Language should still change
                assert manager.get_current_language() == 'en'
                # Other callbacks should still be called
                success_callback.assert_called_once_with('en')


class TestGlobalHelpers:
    """Tests for global helper functions."""

    def test_t_function_uses_global_instance(self, reset_translation_manager):
        """Test that t() function uses global TranslationManager instance."""
        with patch.object(TranslationManager, '_load_language_preference'):
            # Force creation of new instance
            TranslationManager._instance = None
            TranslationManager._initialized = False

            translation = t('app_title')

            assert 'Git Visualizer' in translation

    def test_t_function_with_format_arguments(self, reset_translation_manager):
        """Test that t() function handles format arguments."""
        with patch.object(TranslationManager, '_load_language_preference'):
            translation = t('loaded_commits', 10)

            assert '10' in translation

    def test_get_translation_manager_creates_instance(self, reset_translation_manager):
        """Test that get_translation_manager() creates instance if needed."""
        with patch.object(TranslationManager, '_load_language_preference'):
            # Force reset
            TranslationManager._instance = None

            manager = get_translation_manager()

            assert manager is not None
            assert isinstance(manager, TranslationManager)


class TestSettingsDirectory:
    """Tests for settings directory management."""

    def test_get_settings_dir_creates_directory(self, reset_translation_manager, temp_settings_dir):
        """Test that _get_settings_dir creates ~/.gitvys/ if it doesn't exist."""
        # Remove directory
        import shutil
        shutil.rmtree(temp_settings_dir)

        manager = TranslationManager()
        settings_dir = manager._get_settings_dir()

        assert os.path.exists(settings_dir)

    def test_get_settings_file_returns_correct_path(self, reset_translation_manager, temp_settings_dir):
        """Test that _get_settings_file returns correct path."""
        manager = TranslationManager()
        settings_file = manager._get_settings_file()

        # Use os.path.sep for cross-platform compatibility
        expected_ending = os.path.join('.gitvys', 'settings.json')
        assert settings_file.endswith(expected_ending)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_translation_key(self, reset_translation_manager):
        """Test handling of empty translation key."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            translation = manager.get('')

            # Should return empty string
            assert translation == ''

    def test_get_with_none_arguments(self, reset_translation_manager):
        """Test get() with None format arguments."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()

            # Should not crash
            translation = manager.get('app_title', None)

            # Will try to format with None, might work or return key
            assert translation is not None

    def test_unregister_nonexistent_callback(self, reset_translation_manager):
        """Test unregistering callback that doesn't exist."""
        with patch.object(TranslationManager, '_load_language_preference'):
            manager = TranslationManager()
            callback = MagicMock()

            # Should not raise exception
            manager.unregister_callback(callback)

            assert callback not in manager._callbacks
