import os
from marqo.tensor_search import validation
from enum import Enum
from marqo.tensor_search import enums
import unittest
from unittest import mock
from unittest.mock import patch
from marqo.tensor_search.models.score_modifiers_object import ScoreModifier
from marqo.tensor_search.models.delete_docs_objects import MqDeleteDocsRequest
from marqo.tensor_search.models.search import SearchContext
from marqo.errors import (
    InvalidFieldNameError, InternalError,
    InvalidDocumentIdError, InvalidArgError, DocTooLargeError,
    InvalidIndexNameError
)
from marqo.s2_inference import errors as s2_inference_errors

class TestValidation(unittest.TestCase):

    def setUp(self) -> None:
        class SimpleEnum(str, Enum):
            ABC = "APPLE"
            DEF = "BANANA"

        self.SimpleEnum = SimpleEnum

    def test_validate_str_against_enum_case_senstive(self):
        try:
            validation.validate_str_against_enum("banana", self.SimpleEnum, case_sensitive=True)
            raise AssertionError
        except ValueError:
            pass

    def test_validate_str_against_enum_case_insensitive(self):
        assert "banana" == validation.validate_str_against_enum("banana", self.SimpleEnum, case_sensitive=False)

    def test_validate_str_against_enum(self):
        assert "APPLE" == validation.validate_str_against_enum("APPLE", self.SimpleEnum)

    def test_validate_chunk_plus_name(self):
        try:
            validation.validate_field_name("__chunks.__field_name")
            raise AssertionError
        except InvalidFieldNameError as s:
            pass

    def test_nesting_attempt(self):
        try:
            validation.validate_field_name("some_object.__field_name")
            raise AssertionError
        except InvalidFieldNameError as s:
            pass

    def test_validate_field_name_good(self):
        assert "some random fieldname" == validation.validate_field_name("some random fieldname")

    def test_validate_field_name_good_2(self):
        assert "abc__field_name" == validation.validate_field_name("abc__field_name")

    def test_validate_field_name_empty(self):
        try:
            validation.validate_field_name("")
            raise AssertionError
        except InvalidFieldNameError as s:
            pass

    def test_validate_field_name_none(self):
        try:
            validation.validate_field_name(None)
            raise AssertionError
        except InvalidFieldNameError as s:
            pass

    def test_validate_field_name_other(self):
        try:
            validation.validate_field_name(123)
            raise AssertionError
        except InvalidFieldNameError as s:
            assert "must be str" in str(s)

    def test_validate_field_name_protected(self):
        try:
            validation.validate_field_name("__field_name")
            raise AssertionError
        except InvalidFieldNameError as s:
            assert "protected field" in str(s)

    def test_validate_field_name_vector_prefix(self):
        try:
            validation.validate_field_name("__vector_")
            raise AssertionError
        except InvalidFieldNameError as s:
            assert "protected prefix" in str(s)

    def test_validate_field_name_vector_prefix_2(self):
        try:
            validation.validate_field_name("__vector_abc")
            raise AssertionError
        except InvalidFieldNameError as s:
            assert "protected prefix" in str(s)

    def test_validate_doc_empty(self):
        try:
            validation.validate_doc({})
            raise AssertionError
        except InvalidArgError as s:
            pass

    def test_validate_vector_name(self):
        good_name = "__vector_Title 1"
        assert good_name == validation.validate_vector_name(good_name)

    def test_validate_vector_name_2(self):
        """should only try removing the first prefix"""
        good_name = "__vector___vector_1"
        assert good_name == validation.validate_vector_name(good_name)

    def test_validate_vector_name_only_prefix(self):
        bad_vec = "__vector_"
        try:
            validation.validate_vector_name(bad_vec)
            raise AssertionError
        except InternalError as s:
            assert "empty" in str(s)

    def test_validate_vector_empty(self):
        bad_vec = ""
        try:
            validation.validate_vector_name(bad_vec)
            raise AssertionError
        except InternalError as s:
            assert "empty" in str(s)

    def test_validate_vector_int(self):
        bad_vec = 123
        try:
            validation.validate_vector_name(bad_vec)
            raise AssertionError
        except InternalError as s:
            assert 'must be str' in str(s)

        bad_vec_2 = ["efg"]
        try:
            validation.validate_vector_name(bad_vec_2)
            raise AssertionError
        except InternalError as s:
            assert 'must be str' in str(s)

    def test_validate_vector_no_prefix(self):
        bad_vec = "some bad title"
        try:
            validation.validate_vector_name(bad_vec)
            raise AssertionError
        except InternalError as s:
            assert 'vectors must begin' in str(s)

    def test_validate_vector_name_protected_field(self):
        """the vector name without the prefix can't be the name of a protected field"""
        bad_vec = "__vector___chunk_ids"
        try:
            validation.validate_vector_name(bad_vec)
            raise AssertionError
        except InternalError as s:
            assert 'protected name' in str(s)

    def test_validate_vector_name_id_field(self):
        bad_vec = "__vector__id"
        try:
            validation.validate_vector_name(bad_vec)
            raise AssertionError
        except InternalError as s:
            assert 'protected name' in str(s)

    def test_validate_field_name_highlight(self):
        bad_name = "_highlights"
        try:
            validation.validate_field_name(bad_name)
            raise AssertionError
        except InvalidFieldNameError as s:
            assert 'protected field' in str(s)

    def test_validate_field_content_bad(self):
        bad_field_content = [
            {123}, None,['not 100% strings', 134, 1.4, False],
            ['not 100% strings', True]
        ]
        for non_tensor_field in (True, False):
            for bad_content in bad_field_content:
                try:
                    validation.validate_field_content(bad_content, is_non_tensor_field=non_tensor_field)
                    raise AssertionError
                except InvalidArgError as e:
                    pass

    def test_validate_field_content_good(self):
        good_field_content = [
            123, "heehee", 12.4, False
        ]
        for non_tensor_field in (True, False):
            for good_content in good_field_content:
                assert good_content == validation.validate_field_content(good_content, is_non_tensor_field=non_tensor_field)

    def test_validate_field_content_list(self):
        good_field_content = [
            [], [''], ['abc', 'efg', '123'], ['', '']
        ]
        for good_content in good_field_content:
            assert good_content == validation.validate_field_content(good_content, is_non_tensor_field=True)

        for good_content in good_field_content:
            # fails when non tensor field
            try:
                validation.validate_field_content(good_content, is_non_tensor_field=False)
                raise AssertionError
            except InvalidArgError:
                pass



    def test_validate_id_good(self):
        bad_ids = [
            {123}, [], None, {"abw": "cjnk"}, 1234
        ]
        for bad_content in bad_ids:
            try:
                validation.validate_id(bad_content)
                raise AssertionError
            except InvalidDocumentIdError as e:
                pass

    def test_validate_id_bad(self):
        good_ids = [
            "123", "hehee", "12_349"
        ]
        for good_content in good_ids:
            assert good_content == validation.validate_id(good_content)

    def test_validate_doc_max_size(self):
        max_size = 1234567
        mock_environ = {enums.EnvVars.MARQO_MAX_DOC_BYTES: str(max_size)}

        @mock.patch.dict(os.environ, mock_environ)
        def run():
            good_doc = {"abcd": "a" * (max_size - 500)}
            good_back = validation.validate_doc(doc=good_doc)
            assert good_back == good_doc

            bad_doc = {"abcd": "a" * max_size}
            try:
                validation.validate_doc(doc=bad_doc)
                raise AssertionError
            except DocTooLargeError:
                pass
            return True

        assert run()

    def test_index_name_validation(self):
        assert "my-index-name" == validation.validate_index_name("my-index-name")
        bad_names = ['.opendistro_security', 'security-auditlog-', 'security-auditlog-100',
                     '.opendistro_alerting_config', '.opendistro-alerting-config-', '.kibana',
                     '.kibana-2', 'bulk']
        for n in bad_names:
            try:
                validation.validate_index_name(n)
                raise AssertionError
            except InvalidIndexNameError:
                pass

    def test_boost_validation_illegal(self):
        bad_boosts = [
            set(), (), {'': [1.2]},
            {'fine': [1.2], "ok": [1.2, -3], 'bad': [3, 1, -4]},
            {'fine': [1.2], "ok": [1.2, -3], 'bad': []},
            {'fine': [1.2], "ok": [1.2, -3], 'bad': ['1iu']},
            {'bad': ['str']}, {'bad': []}, {'bad': [1, 4, 5]},
        ]
        for search_method in ('TENSOR', 'LEXICAL', 'OTHER'):
            for bad_boost in bad_boosts:
                try:
                    validation.validate_boost(boost=bad_boost, search_method=search_method)
                    raise AssertionError
                except (InvalidArgError, InvalidFieldNameError) as e:
                    pass

    def test_boost_validation_good_boost_bad_method(self):
        good_boosts = [
            {}, {'fine': [1.2], "ok": [1.2, -3]}, {'fine': [1.2]}, {'fine': [1.2, -1]},
            {'fine': [0, 0]}, {'fine': [0]}, {'fine': [-1.3]}
        ]
        for search_method in ('', 'LEXICAL', 'OTHER'):
            for good_boost in good_boosts:
                try:

                    validation.validate_boost(boost=good_boost, search_method=search_method)
                    raise AssertionError
                except (InvalidArgError, InvalidFieldNameError) as e:
                    pass

    def test_boost_validation_good_boosts(self):
        good_boosts = [
            {}, {'fine': [1.2], "ok": [1.2, -3]}, None, {'fine': [1.2]}, {'fine': [1.2, -1]},
        ]
        for good_boost in good_boosts:
            assert good_boost == validation.validate_boost(boost=good_boost, search_method='TENSOR')

    def test_boost_validation_None_ok(self):
        for search_method in ('', 'LEXICAL', 'OTHER', 'TENSOR'):
            assert None is validation.validate_boost(boost=None, search_method=search_method)


class TestValidateSearchableAttributes(unittest.TestCase):

    def setUp(self) -> None:
        self.searchable_attributes = [f"field{i}" for i in range(5)]

    def test_search_method_not_tensor(self):
        validation.validate_searchable_attributes(
            self.searchable_attributes,
            search_method=enums.SearchMethod.LEXICAL
        )

    def test_maximum_searchable_attributes_not_set(self):
        validation.validate_searchable_attributes(
            self.searchable_attributes,
            search_method=enums.SearchMethod.TENSOR
        )

    @patch.dict('os.environ', {**os.environ, **{'MARQO_MAX_SEARCHABLE_TENSOR_ATTRIBUTES': '1'}})
    def test_searchable_attributes_is_none_max_value_set_raise_invalid_arg_error(self):
        try:
            validation.validate_searchable_attributes(
                searchable_attributes=None,
                search_method=enums.SearchMethod.TENSOR
            )
            raise AssertionError("'searchable_attributes' is None, but MARQO_MAX_SEARCHABLE_TENSOR_ATTRIBUTES is set")

        except InvalidArgError as e:
            self.assertTrue("MARQO_MAX_SEARCHABLE_TENSOR_ATTRIBUTES" in e.message)

    @patch.dict('os.environ', {**os.environ, **{'MARQO_MAX_SEARCHABLE_TENSOR_ATTRIBUTES': '1'}})
    def test_searchable_attributes_not_set_but_max_attributes_set__raise_(self):
        with self.assertRaises(InvalidArgError):
            validation.validate_searchable_attributes(
                searchable_attributes=None,
                search_method=enums.SearchMethod.TENSOR
            )


    @patch.dict('os.environ', {**os.environ, **{'MARQO_MAX_SEARCHABLE_TENSOR_ATTRIBUTES': '1'}})
    def test_searchable_attributes_set__use_searchable_attributes(self):
        with self.assertRaises(InvalidArgError):
            validation.validate_searchable_attributes(
                searchable_attributes=self.searchable_attributes,
                search_method=enums.SearchMethod.TENSOR
            )

    @patch.dict('os.environ', {**os.environ, **{'MARQO_MAX_SEARCHABLE_TENSOR_ATTRIBUTES': '6'}})
    def test_searchable_attributes_below_limit(self):
        validation.validate_searchable_attributes(
            searchable_attributes=self.searchable_attributes,
            search_method=enums.SearchMethod.TENSOR
        )


class TestValidateIndexSettings(unittest.TestCase):

    @staticmethod
    def get_good_index_settings():
        return {
            "index_defaults": {
                "treat_urls_and_pointers_as_images": False,
                "model": "hf/all_datasets_v4_MiniLM-L6",
                "normalize_embeddings": True,
                "text_preprocessing": {
                    "split_length": 2,
                    "split_overlap": 0,
                    "split_method": "sentence"
                },
                "image_preprocessing": {
                    "patch_method": None
                }
            },
            "number_of_shards": 5,
            "number_of_replicas":1
        }

    def test_validate_index_settings(self):

        good_settings =[
            {
                "index_defaults": {
                    "treat_urls_and_pointers_as_images": False,
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "normalize_embeddings": True,
                    "text_preprocessing": {
                        "split_length": 2,
                        "split_overlap": 0,
                        "split_method": "sentence"
                    },
                    "image_preprocessing": {
                        "patch_method": None
                    }
                },
                "number_of_shards": 5,
                "number_of_replicas": 1
            },
            {   # extra field in text_preprocessing: OK
                "index_defaults": {
                    "treat_urls_and_pointers_as_images": False,
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "normalize_embeddings": True,
                    "text_preprocessing": {
                        "split_length": 2,
                        "split_overlap": 0,
                        "split_method": "sentence",
                        "blah blah blah": "woohoo"
                    },
                    "image_preprocessing": {
                        "patch_method": None
                    }
                },
                "number_of_shards": 5,
                "number_of_replicas": 1
            },
            {  # extra field in image_preprocessing: OK
                "index_defaults": {
                    "treat_urls_and_pointers_as_images": False,
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "normalize_embeddings": True,
                    "text_preprocessing": {
                        "split_length": 2,
                        "split_overlap": 0,
                        "split_method": "sentence",
                    },
                    "image_preprocessing": {
                        "patch_method": None,
                        "blah blah blah": "woohoo"
                    }
                },
                "number_of_shards": 5,
                "number_of_replicas": 1
            }
        ]
        for settings in good_settings:
            assert settings == validation.validate_settings_object(settings)

    def test_validate_index_settings_model_properties(self):
        good_settings = self.get_good_index_settings()
        good_settings['index_defaults']['model_properties'] = dict()
        assert good_settings == validation.validate_settings_object(good_settings)

    def test_validate_index_settings_bad(self):
        bad_settings = [{
            "index_defaults": {
                "treat_urls_and_pointers_as_images": False,
                "model": "hf/all_datasets_v4_MiniLM-L6",
                "normalize_embeddings": True,
                "text_preprocessing": {
                    "split_length": "2",
                    "split_overlap": "0",
                    "split_method": "sentence"
                },
                "image_preprocessing": {
                    "patch_method": None
                }
            },
            "number_of_shards": 5,
            "number_of_replicas" : -1
        },
        {
            "index_defaults": {
                "treat_urls_and_pointers_as_images": False,
                "model": "hf/all_datasets_v4_MiniLM-L6",
                "normalize_embeddings": True,
                "text_preprocessing": {
                    "split_length": "2",
                    "split_overlap": "0",
                    "split_method": "sentence"
                },
                "image_preprocessing": {
                    "patch_method": None
                }
            },
            "number_of_shards": 5
        },
        ]
        for bad_setting in bad_settings:
            try:
                validation.validate_settings_object(bad_setting)
                raise AssertionError
            except InvalidArgError as e:
                pass

    def test_validate_index_settings_missing_text_preprocessing(self):
        settings = self.get_good_index_settings()
        # base good settings should be OK
        assert settings == validation.validate_settings_object(settings)
        del settings['index_defaults']['text_preprocessing']
        try:
            validation.validate_settings_object(settings)
            raise AssertionError
        except InvalidArgError:
            pass

    def test_validate_index_settings_missing_model(self):
        settings = self.get_good_index_settings()
        # base good settings should be OK
        assert settings == validation.validate_settings_object(settings)
        del settings['index_defaults']['model']
        try:
            validation.validate_settings_object(settings)
            raise AssertionError
        except InvalidArgError:
            pass

    def test_validate_index_settings_missing_index_defaults(self):
        settings = self.get_good_index_settings()
        # base good settings should be OK
        assert settings == validation.validate_settings_object(settings)
        del settings['index_defaults']
        try:
            validation.validate_settings_object(settings)
            raise AssertionError
        except InvalidArgError:
            pass

    def test_validate_index_settings_bad_number_shards(self):
        settings = self.get_good_index_settings()
        # base good settings should be OK
        assert settings == validation.validate_settings_object(settings)
        settings['number_of_shards'] = -1
        try:
            validation.validate_settings_object(settings)
            raise AssertionError
        except InvalidArgError as e:
            pass

    def test_validate_index_settings_bad_number_replicas(self):
        settings = self.get_good_index_settings()
        # base good settings should be OK
        assert settings == validation.validate_settings_object(settings)
        settings['number_of_replicas'] = -1
        try:
            validation.validate_settings_object(settings)
            raise AssertionError
        except InvalidArgError as e:
            pass

    def test_validate_index_settings_img_preprocessing(self):
        settings = self.get_good_index_settings()
        # base good settings should be OK
        assert settings == validation.validate_settings_object(settings)
        settings['index_defaults']['image_preprocessing']["path_method"] = "frcnn"
        assert settings == validation.validate_settings_object(settings)

    def test_validate_index_settings_misplaced_fields(self):
        bad_settings = [
            {
                "index_defaults": {
                    "treat_urls_and_pointers_as_images": False,
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "normalize_embeddings": True,
                    "text_preprocessing": {
                        "split_length": 2,
                        "split_overlap": 0,
                        "split_method": "sentence"
                    },
                    "image_preprocessing": {
                        "patch_method": None
                    }
                },
                "number_of_shards": 5,
                "model": "hf/all_datasets_v4_MiniLM-L6"  # model is also outside, here...
            },
            {
                "index_defaults": {
                    "image_preprocessing": {
                        "patch_method": None  # no models here
                    },
                    "normalize_embeddings": True,
                    "text_preprocessing": {
                        "split_length": 2,
                        "split_method": "sentence",
                        "split_overlap": 0
                    },
                    "treat_urls_and_pointers_as_images": False
                },
                "model": "open_clip/ViT-L-14/laion2b_s32b_b82k", # model here (bad)
                "number_of_shards": 5,
                "treat_urls_and_pointers_as_images": True
            },
            {
                "index_defaults": {
                    "image_preprocessing": {
                        "patch_method": None,
                        "model": "open_clip/ViT-L-14/laion2b_s32b_b82k",
                    },
                    "normalize_embeddings": True,
                    "text_preprocessing": {
                        "split_length": 2,
                        "split_method": "sentence",
                        "split_overlap": 0
                    },
                    "treat_urls_and_pointers_as_images": False,
                    "number_of_shards": 5,  # shouldn't be here
                },
                "treat_urls_and_pointers_as_images": True
            },
            {  # good, BUT extra field in index_defaults
                "index_defaults": {
                    "number_of_shards": 5,
                    "treat_urls_and_pointers_as_images": False,
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "normalize_embeddings": True,
                    "text_preprocessing": {
                        "split_length": 2,
                        "split_overlap": 0,
                        "split_method": "sentence"
                    },
                    "image_preprocessing": {
                        "patch_method": None
                    }
                },
                "number_of_shards": 5
            },
            {  # good, BUT extra field in root
                "model": "hf/all_datasets_v4_MiniLM-L6",
                "index_defaults": {
                    "treat_urls_and_pointers_as_images": False,
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "normalize_embeddings": True,
                    "text_preprocessing": {
                        "split_length": 2,
                        "split_overlap": 0,
                        "split_method": "sentence"
                    },
                    "image_preprocessing": {
                        "patch_method": None
                    }
                },
                "number_of_shards": 5
            }
        ]
        for bad_set in bad_settings:
            try:
                validation.validate_settings_object(bad_set)
                raise AssertionError
            except InvalidArgError as e:
                pass

    def test_validate_mappings(self):
        mappings = [
             {
                "my_combination_field": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": 0.5
                    }
                }
            },
            {
                "my_combination_field": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": 0.5
                    }
                },
                "other_field": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": 0.7,
                        "bugs": 200
                    }
                },
            },
            {},
            {
                " ": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": -2
                    }
                }
            },
            {
                "abcd ": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": -4.6,
                        "other_text": 22
                    }
                }
            },
            {
                "abcd ": {
                    "type": "multimodal_combination",
                    "weights": {}
                }
            },
            {
                "abcd ": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": 0,
                    }
                }
            },

            # Mappings with custom vector
            {
                "my_custom_vector": {
                    "type": "custom_vector"
                }
            },
            # Mappings with both custom vector and multimodal combination
            {
                "my_custom_vector": {
                    "type": "custom_vector"
                },
                "abcd ": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": -4.6,
                        "other_text": 22
                    }
                },
                "my_custom_vector_2": {
                    "type": "custom_vector"
                }
            },

        ]
        for d in mappings:
            assert d == validation.validate_mappings_object(d)


    def test_validate_mappings_invalid(self):
        mappings = [
            {
                "my_combination_field": {
                    "type": "othertype",  # bad type
                    "weights": {
                        "some_text": 0.5

                    }
                }
            },
            # Field with no type
            {
                "my_combination_field": {
                    "weights": {
                        "some_text": 0.5

                    }
                }
            },
            # Empty mapping
            {
                "empty field": {}
            },
            {
                "my_combination_field": {
                    "type": "multimodal_combination",
                    "non_weights": {  # unknown fieldname 'non_weights' config in multimodal_combination
                        "some_text": 0.5
                    }
                }
            },
            {
                "my_combination_field": {
                    "type": "multimodal_combination",
                    # missing weights for multimodal_combination
                }
            },
            {
                "my_combination_field": {
                    "type": "multimodal_combination",
                    "weights": {"blah": "woo"}  # non-number weights
                }
            },
            {
                "my_combination_field": {
                    "type": "multimodal_combination",
                    "weights": {"blah": "1.3"}  # non-number weights
                }
            },
            {
                "abcd ": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": -4.6,
                        "other_text": 22
                    },
                    "extra_field": {"blah"}  # unknown field
                }
            },
            {
                "abcd ": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": -4.6,
                        "other_text": 22,
                        "nontext": True  # non-number
                    },
                }
            },
            { # needs more nesting
                "type": "multimodal_combination",
                "weights": {
                    "some_text": 0.5
                }
            },
            {
                "my_combination_field": { # this dict is OK
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": 0.5
                    }
                },
                "other_field": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": 0.7,
                        "bugs": [0.5, -1.3]  # this is bad array
                    }
                },
            },
            # Custom vector with extra field
            {
                "my_custom_vector": {
                    "type": "custom_vector",
                    "extra_field": "blah"
                }
            },
            # Custom vector with extra field and multimodal
            {
                "my_custom_vector": {
                    "type": "custom_vector",
                    "extra_field_2": "blah"
                },
                "abcd": {
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": -4.6,
                        "other_text": 22
                    }
                }
            },
        ]
        for mapping in mappings:
            try:
                validation.validate_mappings_object(mapping)
                raise AssertionError
            except InvalidArgError as e:
                pass

    def test_valid_multimodal_combination_mappings_object(self):
        mappings = [
            {
                "type": "multimodal_combination",
                "weights": {
                    "some_text": 0.5
                }
            },
            {
                "type": "multimodal_combination",
                "weights": {
                    "some_text": -2
                }
            },
            {
                "type": "multimodal_combination",
                "weights": {
                    "some_text": -4.6,
                    "other_text": 22
                }
            },
            {
                "type": "multimodal_combination",
                "weights": {}
            },
            {
                "type": "multimodal_combination",
                "weights": {
                    "some_text": 0,
                }
            },
        ]
        for d in mappings:
            assert d == validation.validate_multimodal_combination_mappings_object(d)

    def test_invalid_multimodal_combination_mappings_object(self):
        mappings = [
            ({
                "my_combination_field": { # valid mappings dir, but not valid multimodal
                    "type": "multimodal_combination",
                    "weights": {
                        "some_text": 0.5
                    }
                }
            }, "'type' is a required property"),
            ({
                "type": "othertype",  # bad type
                "weights": {
                    "some_text": 0.5

                }
            }, "'othertype' is not one of"),
            ({
                "type": "multimodal_combination",
                "non_weights": {  # unknown fieldname 'non_weights' config in multimodal_combination
                    "some_text": 0.5
                }
            }, "'weights' is a required property"),
            ({
                "type": "multimodal_combination",
                # missing weights for multimodal_combination
            }, "'weights' is a required property"),
            ({
                "type": "multimodal_combination",
                "weights": {"blah": "woo"}  # non-number weights
            }, "is not of type 'number'"),
            ({
                "type": "multimodal_combination",
                "weights": {"blah": "1.3"}  # non-number weights
            }, "is not of type 'number'"),
            ({
                "type": "multimodal_combination",
                "weights": {
                    "some_text": -4.6,
                    "other_text": 22
                },
                "extra_field": {"blah"}  # unknown field
            }, "Additional properties are not allowed"),
            ({
                "type": "multimodal_combination",
                "weights": {
                    "some_text": -4.6,
                    "other_text": 22,
                    "nontext": True  # non-number
                },
            }, "is not of type 'number'")
        ]
        for mapping, error_message in mappings:
            try:
                validation.validate_multimodal_combination_mappings_object(mapping)
                raise AssertionError
            except InvalidArgError as e:
                assert error_message in e.message

    def test_valid_custom_vector_mappings_object(self):
        # There is only 1 valid format for custom vector mapping.
        mappings = [
            {
                "type": "custom_vector"
            }
        ]
        for d in mappings:
            assert d == validation.validate_custom_vector_mappings_object(d)

    def test_invalid_custom_vector_mappings_object(self):
        mappings = [
            # Extra field
            ({
                "type": "custom_vector",
                "extra_field": "blah"
            }, "Additional properties are not allowed ('extra_field' was unexpected)"),
            # Misspelled type field
            ({
                "typeblahblah": "custom_vector",
            }, "'type' is a required property"),
            # Type not custom_vector
            ({
                "type": "the wrong field type",
            }, "'the wrong field type' is not one of"),
            # Empty
            ({}, "'type' is a required property")
        ]
        for mapping, error_message in mappings:
            try:
                validation.validate_custom_vector_mappings_object(mapping)
                raise AssertionError
            except InvalidArgError as e:
                assert error_message in e.message

    def test_validate_valid_context_object(self):
        valid_context_list = [
            {
                "tensor":[
                    {"vector" : [0.2132] * 512, "weight" : 0.32},
                    {"vector": [0.2132] * 512, "weight": 0.32},
                    {"vector": [0.2132] * 512, "weight": 0.32},
                ]
            },
            {
                "tensor": [
                    {"vector": [0.2132] * 512, "weight": 1},
                    {"vector": [0.2132] * 512, "weight": 1},
                    {"vector": [0.2132] * 512, "weight": 1},
                ]
            },

            {
                # Note we are not validating the vector size here
                "tensor": [
                    {"vector": [0.2132] * 53, "weight": 1},
                    {"vector": [23,], "weight": 1},
                    {"vector": [0.2132] * 512, "weight": 1},
                ],
                "addition_field": None
            },
            {
                "tensor": [
                    {"vector": [0.2132] * 53, "weight": 1},
                    {"vector": [23, ], "weight": 1},
                    {"vector": [0.2132] * 512, "weight": 1},
                ],
                "addition_field_1": None,
                "addition_field_2": "random"
            },
            {
                "tensor": [
                             {"vector": [0.2132] * 512, "weight": 0.32},
                         ] * 64
            },
        ]

        for valid_context in valid_context_list:
            SearchContext(**valid_context)

    def test_validate_invalid_context_object(self):
        valid_context_list = [
            # {
            #     # Typo in tensor
            #     "tensors": [
            #         {"vector" : [0.2132] * 512, "weight" : 0.32},
            #         {"vector": [0.2132] * 512, "weight": 0.32},
            #         {"vector": [0.2132] * 512, "weight": 0.32},
            #     ]
            # },
            {
                # Typo in vector
                "tensor": [
                    {"vectors": [0.2132] * 512, "weight": 1},
                    {"vector": [0.2132] * 512, "weight": 1},
                    {"vector": [0.2132] * 512, "weight": 1},
                ]
            },
            {
                # Typo in weight
                "tensor": [
                    {"vector": [0.2132] * 53, "weight": 1},
                    {"vector": [23,], "weight": 1},
                    {"vector": [0.2132] * 512, "weights": 1},
                ],
                "addition_field": None
            },
            {
                # Int instead of list
                "tensor": [
                    {"vector": [0.2132] * 53, "weight": 1},
                    {"vector": [23, ], "weight": 1},
                    {"vector": 3, "weight": 1},
                ],
                "addition_field_1": None,
                "addition_field_2": "random"
            },
            {
                # Str instead of list
                "tensor": [
                    {"vector" : str([0.2132] * 512), "weight": 0.32},
                    {"vector": [0.2132] * 512, "weight": 0.32},
                    {"vector": [0.2132] * 512, "weight": 0.32},
                ],
                "addition_field_1": None,
                "addition_field_2": "random"
            },
            {
                # None instead of list
                "tensor": [
                    {"vector": [0.2132] * 53, "weight": 1},
                    {"vector": [23, ], "weight": 1},
                    {"vectors": None, "weight": 1},
                ],
                "addition_field_1": None,
                "addition_field_2": "random"
            },
            {
                # too many vectors, maximum 64
                "tensor": [
                    {"vector": [0.2132] * 512, "weight": 0.32},
                    ] * 65
            },
            {
                # None
                "tensor": None,
            },
            {
                # Empty tensor
                "tensor": [],
            },
        ]

        for invalid_context in valid_context_list:
            try:
                s = SearchContext(**invalid_context)
                raise AssertionError(invalid_context, s)
            except InvalidArgError:
                pass

    def test_invalid_custom_score_fields(self):
        invalid_custom_score_fields_list = [
            {
                # typo in multiply_score_by
                "multiply_scores_by":
                    [{"field_name": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_to_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # typo in add_to_score
                "multiply_score_by":
                    [{"field_name": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_ssto_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # typo in field_name
                "multiply_score_by":
                    [{"field_names": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_to_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # typo in weight
                "multiply_score_by":
                    [{"field_names": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_to_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # no field name
                "multiply_scores_by":
                    [{"field_names": "reputation",
                      "weights": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],
                "add_ssto_score": [
                    {"field_name": "rate",
                     }],
            },
            {
                # list in field_name value
                "multiply_score_by":
                    [{"field_name": ["repuation", "reputation-test"],
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     },],
                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
            {
                # field name can't be "_id"
                "multiply_score_by":
                    [{"field_name": "_id",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],

                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
            {}, # empty 
            {  # one part to be empty
                "multiply_score_by": [],
                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
            {  # two parts to be empty
                "multiply_score_by": [],
                "add_to_score": [],
            },
        ]
        for invalid_custom_score_fields in invalid_custom_score_fields_list:
            try:
                v = ScoreModifier(**invalid_custom_score_fields)
                raise AssertionError(invalid_custom_score_fields, v)
            except InvalidArgError:
                pass

    def test_valid_custom_score_fields(self):
        valid_custom_score_fields_list = [
            {
                "multiply_score_by":
                    [{"field_name": "reputation",
                      "weight": 1,
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],

                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
            {
                "multiply_score_by":
                    [{"field_name": "reputation",
                      },
                     {
                         "field_name": "reputation-test",
                     }, ],

                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
            {
                # miss one part
                "add_to_score": [
                    {"field_name": "rate",
                     }]
            },
        ]

        for valid_custom_score_fields in valid_custom_score_fields_list:
            ScoreModifier(**valid_custom_score_fields)
    
    def test_validate_dict(self):
        test_mappings = {
            "my_combo_field":{
                "type":"multimodal_combination", 
                "weights":{
                    "test_1":0.5, "test_2":0.5
                }
            },
            "my_custom_vector":{
                "type":"custom_vector"
            }
        }
        field = "my_combo_field"
        valid_dict = {"test_1": "test", "test_2": "test_test"}

        # valid_dict
        validation.validate_dict(field, valid_dict, is_non_tensor_field=False, mappings=test_mappings)

        # invalid str:str format
        # str:list
        try:
            validation.validate_dict(field, {"test_1": ["my","test"], "test_2": "test_test"}, is_non_tensor_field=False, mappings=test_mappings)
            raise AssertionError
        except InvalidArgError as e:
            assert "is not of valid content type" in e.message
        # str:tuple
        try:
            validation.validate_dict(field, {"test_1": ("my","test"), "test_2": "test_test"}, is_non_tensor_field=False,
                          mappings=test_mappings)
            raise AssertionError
        except InvalidArgError as e:
            assert "is not of valid content type" in e.message

        # str:dict
        try:
            validation.validate_dict(field, {"test_1": {"my":"test"}, "test_2": "test_test"}, is_non_tensor_field=False,
                          mappings=test_mappings)
            raise AssertionError
        except InvalidArgError as e:
            assert "is not of valid content type" in e.message

        # str:int
        try:
            validation.validate_dict(field, {"test_1": 53213, "test_2": "test_test"}, is_non_tensor_field=False,
                          mappings=test_mappings)
            raise AssertionError
        except InvalidArgError as e:
            assert "is not of valid content type" in e.message

        # str:None
        try:
            validation.validate_dict(field, {"test_1": None, "test_2": "test_test"}, is_non_tensor_field=False,
                          mappings=test_mappings)
            raise AssertionError
        except InvalidArgError as e:
            assert "is not of valid content type" in e.message

        # mapping is None
        try:
            validation.validate_dict(field, valid_dict, is_non_tensor_field=False, mappings=None)
            raise AssertionError
        except InvalidArgError as e:
            assert "the parameter `mappings`" in e.message

        # field not in mappings
        try:
            validation.validate_dict('void_field', valid_dict, is_non_tensor_field=False, mappings=test_mappings)
            raise AssertionError
        except InvalidArgError as e:
            assert "must be in the add_documents `mappings` parameter" in e.message

        # sub_fields not in mappings["weight"]
        try:
            validation.validate_dict(field, {"test_void": "test", "test_2": "test_test"}, is_non_tensor_field=False, mappings=test_mappings)
            raise AssertionError
        except InvalidArgError as e:
            assert "Each sub_field requires a weight" in e.message

        # length of fields
        try:
            validation.validate_dict(field, {}, is_non_tensor_field=False, mappings=test_mappings)
            raise AssertionError
        except InvalidArgError as e:
            assert "it must contain at least 1 field" in e.message

        # nontensor_field
        try:
            validation.validate_dict(field, valid_dict, is_non_tensor_field=True, mappings=test_mappings)
            raise AssertionError
        except InvalidArgError as e:
            assert "must be a tensor field" in e.message
        
        # Field in mappings, but type is not valid (multimodal_combination or custom_vector)
        try:
            validation.validate_dict("bad_field", 
                                     {
                                        "nothing": "really matters",
                                        "anyone": "can see",
                                        "nothing, ": "really matters",
                                        "to": "me"
                                     }, 
                                     is_non_tensor_field=True, 
                                     mappings={
                                         "bad_field": {
                                                "type": "invalid_type"
                                         }
                                     })
            raise AssertionError
        except InvalidArgError as e:
            assert "is of invalid type in the `mappings` parameter" in e.message

        # ============== custom vector validate_dict tests ==============
        index_model_dimensions = 384
        # custom vector, valid
        obj = {"content": "custom content is here!!", "vector": [1.0 for _ in range(index_model_dimensions)]}
        assert validation.validate_dict(field="my_custom_vector",
                                    field_content=obj, 
                                    is_non_tensor_field=False,
                                    mappings=test_mappings,
                                    index_model_dimensions=index_model_dimensions) == obj
        
        # custom vector, valid (no content). must be filled with empty string
        obj = {"vector": [1.0 for _ in range(index_model_dimensions)]}
        assert validation.validate_dict(field="my_custom_vector",
                                    field_content=obj, 
                                    is_non_tensor_field=False,
                                    mappings=test_mappings,
                                    index_model_dimensions=index_model_dimensions) \
                == {"content": "", "vector": [1.0 for _ in range(index_model_dimensions)]}
        
        invalid_custom_vector_objects = [
            # Wrong vector length
            ({"content": "custom content is here!!", "vector": [1.0, 1.0, 1.0]}, "is too short"),
            ({"content": "custom content is here!!", "vector": [1.0]*1000}, "is too long"),
            # Wrong content type
            ({"content": 12345, "vector": [1.0 for _ in range(index_model_dimensions)]}, "12345 is not of type 'string'"),
            # Wrong vector type inside list (even if correct length)
            ({"content": "custom content is here!!", "vector": [1.0 for _ in range(index_model_dimensions-1)] + ["NOT A FLOAT"]}, "'NOT A FLOAT' is not of type 'number'"),
            # Field that shouldn't be there
            ({"content": "custom content is here!!", "vector": [1.0 for _ in range(index_model_dimensions)], "extra_field": "blah"}, "Additional properties are not allowed ('extra_field' was unexpected)"),
            # No vector
            ({"content": "custom content is here!!"}, "'vector' is a required property"),
            # Nested dict inside custom vector content
            ({
                "content": {
                    "content": "custom content is here!!",
                    "vector": [1.0 for _ in range(index_model_dimensions)]
                }, 
                "vector": [1.0 for _ in range(index_model_dimensions)]
            }, "is not of type 'string'"),
        ]
        for case, error_message in invalid_custom_vector_objects:
            try:
                validation.validate_dict(field="my_custom_vector",
                                         field_content=case, 
                                         is_non_tensor_field=False,
                                         mappings=test_mappings,
                                         index_model_dimensions=index_model_dimensions)
                raise AssertionError(case)
            except InvalidArgError as e:
                assert error_message in e.message
        
        # No index model dimensions
        try:
            validation.validate_dict(field="my_custom_vector",
                                     field_content={"content": "custom content is here!!", "vector": [1.0 for _ in range(index_model_dimensions)]}, 
                                     is_non_tensor_field=False,
                                     mappings=test_mappings,
                                     index_model_dimensions=None)
            raise AssertionError
        except InternalError as e:
            assert "Index model dimensions should be an `int`" in e.message
            
        # Non-int index model dimensions
        try:
            validation.validate_dict(field="my_custom_vector",
                                     field_content={"content": "custom content is here!!", "vector": [1.0 for _ in range(index_model_dimensions)]}, 
                                     is_non_tensor_field=False,
                                     mappings=test_mappings,
                                     index_model_dimensions="wrong type")
            raise AssertionError
        except InternalError as e:
            assert "Index model dimensions should be an `int`" in e.message


class TestValidateDeleteDocsRequest(unittest.TestCase):

    def setUp(self) -> None:
        self.max_delete_docs_count = 10

    def test_valid_delete_request(self):
        delete_request = MqDeleteDocsRequest(index_name="my_index", document_ids=["id1", "id2", "id3"], auto_refresh=True)
        result = validation.validate_delete_docs_request(delete_request, self.max_delete_docs_count)
        self.assertEqual(delete_request, result)

    def test_invalid_delete_request_not_instance(self):
        delete_request = {"index_name": "my_index", "document_ids": ["id1", "id2", "id3"], "auto_refresh": True}
        with self.assertRaises(RuntimeError):
            validation.validate_delete_docs_request(delete_request, self.max_delete_docs_count)

    def test_invalid_max_delete_docs_count(self):
        delete_request = MqDeleteDocsRequest(index_name="my_index", document_ids=["id1", "id2", "id3"], auto_refresh=True)
        with self.assertRaises(RuntimeError):
            validation.validate_delete_docs_request(delete_request, "10")

    def test_empty_document_ids(self):
        delete_request = MqDeleteDocsRequest(index_name="my_index", document_ids=[], auto_refresh=True)
        with self.assertRaises(InvalidDocumentIdError):
            validation.validate_delete_docs_request(delete_request, self.max_delete_docs_count)

    def test_document_ids_not_sequence(self):
        delete_request = MqDeleteDocsRequest(index_name="my_index", document_ids="id1", auto_refresh=True)
        with self.assertRaises(InvalidArgError):
            validation.validate_delete_docs_request(delete_request, self.max_delete_docs_count)

    def test_exceed_max_delete_docs_count(self):
        delete_request = MqDeleteDocsRequest(index_name="my_index", document_ids=["id{}".format(i) for i in range(1, 12)], auto_refresh=True)
        with self.assertRaises(InvalidArgError):
            validation.validate_delete_docs_request(delete_request, self.max_delete_docs_count)

    def test_invalid_document_id_type(self):
        delete_request = MqDeleteDocsRequest(index_name="my_index", document_ids=["id1", 2, "id3"], auto_refresh=True)
        with self.assertRaises(InvalidDocumentIdError):
            validation.validate_delete_docs_request(delete_request, self.max_delete_docs_count)

    def test_empty_document_id(self):
        delete_request = MqDeleteDocsRequest(index_name="my_index", document_ids=["id1", "", "id3"], auto_refresh=True)
        with self.assertRaises(InvalidDocumentIdError):
            validation.validate_delete_docs_request(delete_request, self.max_delete_docs_count)

    def test_no_limit(self):
        # the default limit is 10000,
        delete_request = MqDeleteDocsRequest(
            index_name="my_index", document_ids=["id{}".format(i) for i in range(1, 20000)], auto_refresh=True)
        with self.assertRaises(RuntimeError):
            validation.validate_delete_docs_request(delete_request, None)


class TestValidateModelProperties(unittest.TestCase):
    def test_validate_model_properties_no_model(self):
        """
        Tests model properties if model="no_model"
        """
        # Invalid cases
        test_cases = [
            # None
            (
                None,
                "must provide `model_properties`"
            ),
            # No dimensions key
            (
                {
                    "dimension": 123
                },
                "must have `dimensions` set"
            ),
            # Extra key
            (
                {
                    "dimensions": 123,
                    "url": "http://www.blah.com"
                },
                "Invalid model_properties key found: `url`"
            )
        ]

        for case, error_message in test_cases:
            try:
                validation.validate_model_properties_no_model(case)
                raise AssertionError
            except InvalidArgError as e:
                assert error_message in e.message

        # Ensure valid case passes
        validation.validate_model_properties_no_model({
            "dimensions": 123
        })
    
    def test_validate_model_name_and_properties(self):
        # Invalid cases
        invalid_cases = [
            # model_properties but no model
            (
                {
                    "index_defaults": {
                        "model_properties": {
                            "dimensions": 123,
                            "url": "http://www.random_model_here.com"
                        }
                    }
                },
                "No `model` found for model_properties"
            ),
            # search_model but no model
            (
                {
                    "index_defaults": {
                        "search_model": "hf/all_datasets_v4_MiniLM-L6"
                    }
                },
                "`search_model` cannot be specified without also specifying `model`"
            ),
            # search_model_properties but no search_model
            (
                {
                    "index_defaults": {
                        "model": "hf/all_datasets_v4_MiniLM-L6",
                        "search_model_properties": {
                            "dimensions": 123,
                            "url": "http://www.random_model_here.com"
                        }
                    }
                },
                "No `search_model` found for search_model_properties"
            ),
        ]

        for case, error_message in invalid_cases:
            try:
                validation.validate_model_name_and_properties(case)
                raise AssertionError
            except InvalidArgError as e:
                assert error_message in e.message

        # Valid cases
        valid_cases = [
            # model and model_properties
            {
                "index_defaults": {
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "model_properties": {
                        "dimensions": 123,
                        "url": "http://www.random_model_here.com"
                    }
                }
            },

            # model, model_properties, and search_model
            {
                "index_defaults": {
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "model_properties": {
                        "dimensions": 123,
                        "url": "http://www.random_model_here.com"
                    },
                    "search_model": "hf/all-MiniLM-L6-v2"
                }
            },

            # model, model_properties, search_model, search_model_properties
            {
                "index_defaults": {
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "model_properties": {
                        "dimensions": 123,
                        "url": "http://www.random_model_here.com"
                    },
                    "search_model": "hf/all-MiniLM-L6-v2",
                    "search_model_properties": {
                        "dimensions": 456,
                        "url": "http://www.random_model_here.com"
                    },
                }
            },

            # model, search_model
            {
                "index_defaults": {
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "search_model": "hf/all-MiniLM-L6-v2",
                }
            },

            # model, search_model, search_model_properties
            {
                "index_defaults": {
                    "model": "hf/all_datasets_v4_MiniLM-L6",
                    "search_model": "hf/all-MiniLM-L6-v2",
                    "search_model_properties": {
                        "dimensions": 456,
                        "url": "http://www.random_model_here.com"
                    },
                }
            },
        ]

        for case in valid_cases:
            validation.validate_model_name_and_properties(case)