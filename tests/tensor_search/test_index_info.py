import pprint
import unittest
from marqo.tensor_search.models.index_info import IndexInfo
from marqo.tensor_search.models import index_info
from marqo.tensor_search.enums import IndexSettingsField as NsFields, TensorField
from marqo.tensor_search import configs
from marqo import errors
import copy


class TestIndexInfo(unittest.TestCase):

    def test_get_vector_properties_empty(self):
        """This shouldn't happen, because there would at least be __field_name from
        index creation"""
        ii = IndexInfo(model_name='a', search_model_name=None, properties=dict(),
                       index_settings=configs.get_default_index_settings())
        try:
            ii.get_vector_properties()
            raise AssertionError
        except KeyError as e:
            assert TensorField.chunks in str(e)

    def test_get_text_properties_empty(self):
        """Text properties aren't nested, so it handles empty properties fine. (no KeyError)"""
        ii = IndexInfo(model_name='a', search_model_name=None, properties=dict(),
                       index_settings=configs.get_default_index_settings())
        assert dict() == ii.get_text_properties()

    def test_get_vector_properties(self):
        ii = IndexInfo(
            model_name='a',
            search_model_name=None, 
            properties={
                "a": {1: 2}, "b": {1: 2},
                TensorField.chunks: {"properties":{
                    "__vector_a": {1: 2},
                    TensorField.field_name: {'a': 'b'}, TensorField.field_content: {"a": "b"}}}},
            index_settings=configs.get_default_index_settings()
        )
        assert {"__vector_a": {1: 2}} == ii.get_vector_properties()

    def test_get_vector_properties_tricky_names(self):
        ii = IndexInfo(
            model_name='a', 
            search_model_name=None, 
            properties={
                "a": {1: 2},
                TensorField.chunks: {"properties": {
                    TensorField.field_name: {'a': 'b'},
                    TensorField.field_content: {"a": "b"},
                    "__vector_a": {1: 2}, "__vector_Some title": {1: 2},
                }}
            }, index_settings=configs.get_default_index_settings()
        )
        assert {"__vector_a": {1: 2},
                "__vector_Some title": {1: 2}} == ii.get_vector_properties()

    def test_get_vector_properties_no_vectors(self):
        ii = IndexInfo(model_name='a', search_model_name=None, properties={
            "a": {1: 2}, "b_a": {1: 2}, "blah blah": {1: 2},
            TensorField.chunks: {"properties": {
                TensorField.field_name: {'a': 'b'},
                TensorField.field_content: {"a": "b"},
            }}
        }, index_settings=configs.get_default_index_settings())
        assert dict() == ii.get_vector_properties()

    def test_get_text_properties(self):
        ii = IndexInfo(
            model_name='a', search_model_name=None,
            properties={
                "a": {1: 2}, "b_a": {1: 2}, "blah blah": {1: 2},
                TensorField.chunks: {"properties": {
                    TensorField.field_name: {'a': 'b'},
                    TensorField.field_content: {"a": "b"},
                }}
            },
            index_settings=configs.get_default_index_settings()
       )
        assert {"a": {1: 2}, "blah blah": {1: 2},
                "b_a": {1: 2}} == ii.get_text_properties()

    def test_get_text_properties_no_text_props(self):
        ii = IndexInfo(
            model_name='some model', search_model_name="some other model",
            properties={
                "__vector_a": {1: 2}, "__vector_b_a": {1: 2},  "__vector_blah blah": {1: 2},
                "__field_name": {1:2},
                TensorField.chunks: {TensorField.field_name: {'a': 'b'}, TensorField.field_content: {"a": "b"}}
            }, index_settings=configs.get_default_index_settings())
        assert dict() == ii.get_text_properties()

    def test_get_text_properties_some_text_props(self):
        ii = IndexInfo(
            model_name='some model', search_model_name=None, 
            properties={
            "__vector_a": {1: 2}, "__vector_b_a": {1: 2},  "__vector_blah blah": {1: 2},
            "__field_name": {1: 2}, "some_text_prop": {1:2334}, "cat": {"hat": "ter"},
            "__doc_chunk_relation": {"afafa": "afafa"},
            TensorField.chunks: {TensorField.field_name: {'a': 'b'}, TensorField.field_content: {"a": "b"}}
            },
            index_settings=configs.get_default_index_settings()
        )
        assert {"some_text_prop": {1:2334}, "cat": {"hat": "ter"}} == ii.get_text_properties()

    def test_get_ann_parameters__default_index_param(self):
        ii = IndexInfo(
            model_name='some model', search_model_name=None,
            properties={},
            index_settings=configs.get_default_index_settings()
        )
        assert ii.get_ann_parameters() == configs.get_default_ann_parameters()

    def test_get_ann_parameters__without_default_ann_parameters__use_defaults(self):
        index_settings = configs.get_default_index_settings()
        del index_settings[NsFields.index_defaults][NsFields.ann_parameters]

        ii = IndexInfo(
            model_name='some model', search_model_name=None,
            properties={},
            index_settings=index_settings
        )
        assert ii.get_ann_parameters() == configs.get_default_ann_parameters()

    def test_get_ann_parameters__use_specified_index_settings__overide_defaults(self):
        index_settings = configs.get_default_index_settings()
        index_settings[NsFields.index_defaults][NsFields.ann_parameters][NsFields.ann_method_name] = "not-hnsw"

        ii = IndexInfo(
            model_name='some model', search_model_name=None,
            properties={},
            index_settings=index_settings
        )
        actual = ii.get_ann_parameters()
        default = configs.get_default_ann_parameters()
        assert actual[NsFields.ann_method_name] == "not-hnsw"
        
        del actual[NsFields.ann_method_name]
        del default[NsFields.ann_method_name]

        assert actual == default

    def test_get_ann_parameters__use_specified_ann_method_parameters__default_unspecified_values(self):
        index_settings = configs.get_default_index_settings()
        index_settings[NsFields.index_defaults][NsFields.ann_parameters][NsFields.ann_method_parameters] = {
            NsFields.hnsw_ef_construction: 1,
            NsFields.hnsw_m: 2
        }

        ii = IndexInfo(
            model_name='some model', search_model_name=None,
            properties={},
            index_settings=index_settings
        )
        default = configs.get_default_ann_parameters()
        actual = ii.get_ann_parameters()
        assert actual[NsFields.ann_method_parameters] == {
            NsFields.hnsw_ef_construction: 1,
            NsFields.hnsw_m: 2
        }
        del actual[NsFields.ann_method_parameters]
        del default[NsFields.ann_method_parameters]
        
        assert actual == default
    
    def test_get_search_model_properties(self):

        default_settings = configs.get_default_index_settings()
        
        # Registry search model
        index_settings = copy.deepcopy(default_settings)
        index_settings[NsFields.index_defaults][NsFields.model] = 'RN101'     # some randomclip model in registry
        index_settings[NsFields.index_defaults][NsFields.search_model] = 'RN50'     # clip model in registry

        ii = IndexInfo(
            model_name='RN101', search_model_name='RN50',
            properties={},
            index_settings=index_settings
        )

        assert ii.get_search_model_properties() == {
            "name": "RN50",
            "dimensions": 1024,
            "notes": "CLIP resnet50",
            "type": "clip",
        }

        # Custom search model
        index_settings = copy.deepcopy(default_settings)
        index_settings[NsFields.index_defaults][NsFields.search_model] = "my_custom_search_model"
        index_settings[NsFields.index_defaults][NsFields.search_model_properties] = {
            "name": "ViT-B-32-quickgelu",
            "dimensions": 512,
            "url": "https://github.com/mlfoundations/open_clip/releases/download/v0.2-weights/vit_b_32-quickgelu-laion400m_avg-8a00ab3c.pt",
            "type": "open_clip",
        }

        ii = IndexInfo(
            model_name='my_custom_model', search_model_name="my_custom_search_model",
            properties={},
            index_settings=index_settings
        )

        assert ii.get_search_model_properties() == {
            "name": "ViT-B-32-quickgelu",
            "dimensions": 512,
            "url": "https://github.com/mlfoundations/open_clip/releases/download/v0.2-weights/vit_b_32-quickgelu-laion400m_avg-8a00ab3c.pt",
            "type": "open_clip",
        }

        # None search model
        index_settings = copy.deepcopy(default_settings)

        ii = IndexInfo(
            model_name='my_custom_model', search_model_name=None,
            properties={},
            index_settings=index_settings
        )

        try:
            ii.get_search_model_properties()
            raise AssertionError
        except errors.InternalError as e:
            assert "Cannot get `search_model_properties` when `search_model` does not exist." in e.message