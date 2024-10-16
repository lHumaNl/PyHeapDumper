import gc
import math
import os
import sys
import json
import time
import traceback
import types
from decimal import Decimal
from fractions import Fraction
from typing import Optional, Any, Dict, Set


class HeapDumper:
    """
    Class for creating and saving heap dumps in JSON format,
    collecting metadata of Python objects in memory.
    """

    @classmethod
    def collect_heap_metadata(cls, file_name: str) -> str:
        """
        Collects metadata from all objects currently in memory,
        including additional code objects, and saves it as a JSON file.

        Args:
            file_name (str): The name of the file where the heap dump will be saved.

        Returns:
            str: A message indicating the success of saving the heap dump.
        """
        try:
            start_time = time.time()

            gc.collect()
            objects = gc.get_objects()
            objects.extend(cls.__get_code_objects())

            metadata_dict = {}
            for obj in objects:
                metadata_dict.setdefault(str(type(obj)), {})[id(obj)] = cls.__get_object_metadata(obj)

            file_name = cls.__save_heap_dump(file_name, metadata_dict)
            file_size = os.path.getsize(file_name)
            file_size_mb = file_size / (1024 * 1024)

            end_time = time.time()

            return (f'Heap dump "{file_name}" saved in {end_time - start_time:.2f} seconds. '
                    f'JSON size: {file_size_mb:.2f}MB')
        except Exception as e:
            tb = os.linesep.join(traceback.format_exc().split(os.linesep))

            raise Exception(f'Failed to save heap dump "{file_name}": {e}\n{tb}')

    @staticmethod
    def __safe_getattr(obj, attr) -> Optional[Any]:
        """
        Safely retrieves an attribute from an object, returning None if an error occurs.

        Args:
            obj: The object from which to retrieve the attribute.
            attr (str): The name of the attribute to retrieve.

        Returns:
            Optional[Any]: The attribute value or None if an error occurs.
        """
        try:
            return getattr(obj, attr)
        except Exception:
            return None

    @staticmethod
    def __safe_isinstance(obj, types_) -> bool:
        """
        Safely checks if an object is an instance of a specified type,
        handling exceptions gracefully.

        Args:
            obj: The object to check.
            types_ (Union[type, Tuple[type, ...]]): The type or tuple of types to check against.

        Returns:
            bool: True if the object is an instance of the specified type(s), False otherwise.
        """
        try:
            return isinstance(obj, types_)
        except Exception:
            return False

    @classmethod
    def __get_code_objects(cls) -> Set:
        """
        Collects all code objects (functions, methods) currently loaded in memory.

        Returns:
            Set: A set of code objects found in the current Python environment.
        """
        code_objects = set()
        for module in list(sys.modules.values()):
            if module is None:
                continue

            code_objects.update(
                cls.__safe_getattr(func, '__code__')
                for func_name in dir(module)

                for func in [cls.__safe_getattr(module, func_name)]

                if cls.__safe_isinstance(func, types.FunctionType)
                and cls.__safe_getattr(func, '__code__') is not None
            )

            code_objects.update(
                cls.__safe_getattr(method, '__code__')
                for cls_name in dir(module)
                for cls_attr in [cls.__safe_getattr(module, cls_name)]

                if cls.__safe_isinstance(cls_attr, type)

                for attr_name in dir(cls_attr)
                for method in [cls.__safe_getattr(cls_attr, attr_name)]

                if cls.__safe_isinstance(method, (types.FunctionType, types.MethodType))
                and cls.__safe_getattr(method, '__code__') is not None
            )

        code_objects.discard(None)

        return code_objects

    @staticmethod
    def __save_heap_dump(file_name: str, metadata_dict: Dict) -> str:
        """
        Saves the heap metadata dictionary as a JSON file.

        Args:
            file_name (str): The name of the file where the heap dump will be saved.
            metadata_dict (Dict): A dictionary containing heap metadata.

        Returns:
            str
        """
        dir_name = os.path.dirname(file_name)

        if dir_name != '':
            os.makedirs(dir_name, exist_ok=True)

        if not file_name.endswith('.json'):
            file_name += '.json'

        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(json.dumps(metadata_dict, ensure_ascii=False))

        return file_name

    @classmethod
    def __get_src_info(cls, obj) -> Dict:
        """
        Retrieves source information (filename, line number, function name) of the object,
        if applicable.

        Args:
            obj: The object to retrieve source information from.

        Returns:
            Dict: A dictionary containing source information.
        """
        if cls.__safe_isinstance(obj, (types.FunctionType, types.MethodType)):
            code = cls.__safe_getattr(obj, '__code__')
            src_info = {key: value for key, value in {
                'co_name': code.co_name if code else None,
                'co_filename': code.co_filename if code else None,
                'co_lineno': code.co_firstlineno if code else None
            }.items() if value is not None}

        elif cls.__safe_isinstance(obj, (type, types.ModuleType)):
            src_info = {key: value for key, value in {
                'co_name': cls.__safe_getattr(obj, '__name__'),
                'co_filename': cls.__safe_getattr(obj, '__file__'),
            }.items() if value is not None}

        elif hasattr(obj, '__class__'):
            cls_obj = obj.__class__
            code = cls.__safe_getattr(cls.__safe_getattr(cls_obj, '__init__'), '__code__')
            src_info = {key: value for key, value in {
                'co_name': code.co_name if code else cls_obj.__name__,
                'co_filename': code.co_filename if code else cls.__safe_getattr(
                    sys.modules.get(cls.__safe_getattr(cls_obj, '__module__')), '__file__'),
                'co_lineno': code.co_firstlineno if code else None
            }.items() if value is not None}

        else:
            src_info = {}

        return src_info

    @classmethod
    def __get_object_metadata(cls, obj) -> Dict:
        """
        Collects metadata for a specific object, including its size, attributes,
        references, and source code information.

        Args:
            obj: The object to collect metadata from.

        Returns:
            Dict: A dictionary containing metadata about the object.
        """
        obj_metadata = {'size': sys.getsizeof(obj)}

        if hasattr(obj, '__dict__') and obj.__dict__:
            obj_metadata['attr'] = {
                attr_name: (
                    attr_value if isinstance(attr_value, (int, bool))
                    else (
                        attr_value if math.isfinite(attr_value) else str(attr_value)
                    ) if isinstance(attr_value, float)
                    else attr_value[:1000] if isinstance(attr_value, str)
                    else str(attr_value[:1000]) if isinstance(attr_value, (memoryview, bytes))
                    else str(attr_value) if isinstance(attr_value, (Decimal, Fraction, complex))
                    else str(list(attr_value)[:1000]) if isinstance(attr_value, range)
                    else None if attr_value is None
                    else [str(type(attr_value)), id(attr_value)]
                )
                for attr_name, attr_value in obj.__dict__.items()
            }
        elif isinstance(obj, types.CodeType):
            obj_metadata['attr'] = {
                'co_name': obj.co_name,
                'co_filename': obj.co_filename,
                'co_firstlineno': obj.co_firstlineno
            }

        references = gc.get_referents(obj)
        if references:
            obj_metadata['ref'] = [
                ref if cls.__safe_isinstance(ref, (int, bool))
                else (
                    ref if math.isfinite(ref) else str(ref)
                ) if cls.__safe_isinstance(ref, float)
                else ref[:1000] if cls.__safe_isinstance(ref, str)
                else str(ref[:1000]) if cls.__safe_isinstance(ref, (memoryview, bytes))
                else str(ref) if cls.__safe_isinstance(ref, (Decimal, Fraction, complex))
                else str(list(ref)[:1000]) if cls.__safe_isinstance(ref, range)
                else None if ref is None
                else [str(type(ref)), id(ref)]
                for ref in references
            ]

        src_info = cls.__get_src_info(obj)
        if src_info:
            obj_metadata['src'] = src_info

        return obj_metadata
