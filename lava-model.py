# This model is for use "AS-IS", and hosted on https://github.com/therealadityashankar/lavadantic-base-model, under the MIT license
# there's no download option cause its meant to be customizable and easy to use
from typing import Callable, Generator, Union, List
from pydantic import BaseModel as PydanticBaseModel
from functools import wraps
from google.cloud.firestore_v1.base_collection import BaseCollectionReference
from google.cloud.firestore_v1.base_document import BaseDocumentReference

class LavaException(Exception): pass
class MultipleValuesLavaException(LavaException): pass

class BaseModel(PydanticBaseModel):
    """
    A pydantic model for easy firebase access!
    """
    _collection : BaseCollectionReference
    id : str

    @classmethod
    def from_dict(cls, id:str, _dict: dict):
        """
        create an object from a class and dictionary

        Parameters
        ----------
        id : str
        The ID of the class model

        _dict : dictionary
        the data required in the class model

        Returns
        -------
        an object of this class
        """
        return cls(id=id, **_dict)

    @classmethod
    def get_from_firestore_document(cls, doc:BaseDocumentReference) -> BaseModel:
        """
        get a class model from a firestore document
        """
        return cls.from_dict(doc.id, doc.to_dict())

    @classmethod
    def get_from_firestore_documents(cls, docs: List[BaseDocumentReference]) -> List[BaseModel]:
        """
        convert many class models to firestore documents
        """
        return [cls.get_from_firestore_document(doc) for doc in docs]

    @classmethod
    def stream_from_firestore_documents(cls, docs: List[BaseDocumentReference]) -> List[BaseModel]:
        """
        convert many class models to firestore documents, while streaming them
        """
        return (cls.get_from_firestore_document(doc) for doc in docs)

    @classmethod
    def get_by_id(cls, id:str) -> Union[None, BaseModel]:
        """
        get a class document from its collection id
        """
        doc = cls._collection.document(id).get()

        if doc.exists:
            return cls.get_from_firestore_document(doc)
        
        return None

    @classmethod
    def lavaify(cls, enforce_one_or_none:Union[bool, Callable]=False):
        """
        wrapper on functions to convert the output to a lava-model from a firebase model

        The callable must have a return type of a list with firestore documents, a generator with firstore documents,
        or a single firestore document

        Parameters
        ----------
        enforce_one_or_none
        requires the output to be a list/generator, 
        forces that the output has only one value, if multiple values are present

        this also makes the output into a single value, rather than multiple values
        it raises MultipleValuesLavaException

        Usage
        -----
        @lavaify
        def get_berries():
            ...
        """
        if callable(enforce_one_or_none):
            return cls.lavaify()(enforce_one_or_none)
        
        def wrapper(f : Callable):
            @wraps(f)
            def func(*args, **kwargs):
                val = f()

                if not enforce_one_or_none:
                    if isinstance(val, list):
                        return cls.get_from_firestore_documents(val)

                    elif isinstance(val, Generator):
                        return cls.stream_from_firestore_documents(val)

                    elif isinstance(val, BaseDocumentReference):
                        return cls.get_from_firestore_document(val)
                    
                    else:
                        raise ValueError("Invalid document type, must be a single firestore document, or a list or generator of firestore documents")
                else:
                    if isinstance(val, list):
                        if len(val) > 1:
                            raise MultipleValuesLavaException("multiple values present, expected a single value")
                        
                        elif len(val) == 1:
                            return cls.get_from_firestore_document(val[0])
                        
                        else:
                            return None

                    elif isinstance(val, Generator):
                        val = [*val]
                        if len(val) > 1:
                            raise MultipleValuesLavaException("multiple values present, expected a single value")
                        
                        elif len(val) == 1:
                            return cls.get_from_firestore_document(val[0])
                        
                        else:
                            return None
                    
                    else:
                        raise ValueError("Invalid document type, must be  a list or generator of firestore documents, when enforce_one_or_none is true")

        return wrapper

    @classmethod
    def get_one_or_none_where(cls, param_check : str, param_value : str) -> Union[None, BaseModel]:
        """
        Gets One or None value for a "where" "==" firebase match

        Parameters
        ----------
        param_check
        the parameter to check

        param_value:
        the value to check against

        Raises
        ------
        MultipleValuesLavaException, when you get more than one value
        """
        values = cls._collection.where(param_check, "==", param_value).get()

        if len(values) > 1:
            raise MultipleValuesLavaException("multiple values exist, expected only one value")

        if len(values) == 1:
            return cls.get_from_firestore_document(values[0])

        return None

    def save(self) -> None:
        """saves the document to firestore"""
        self._collection.document(self.id).set(self.to_dict())

    def firedict(self) -> dict:
        values = self.dict()
        del values["id"]
        return values
    
