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
from typing import Optional, Any, Dict, Set, List


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
        """
        try:
            return getattr(obj, attr)
        except BaseException:
            return None

    @staticmethod
    def __safe_isinstance(obj, types_) -> bool:
        """
        Safely checks if an object is an instance of a specified type.
        """
        try:
            return isinstance(obj, types_)
        except BaseException:
            return False

    @staticmethod
    def __safe_dir(obj) -> List[str]:
        """
        Safely retrieves the list of attributes from an object.
        """
        try:
            return dir(obj)
        except BaseException:
            return []

    @classmethod
    def __get_code_objects(cls) -> Set:
        """
        Collects all code objects (functions, methods) currently loaded in memory.
        """
        code_objects = set()
        for module in list(sys.modules.values()):
            if module is None:
                continue

            # Collect code objects from module-level functions
            code_objects.update(
                cls.__safe_getattr(func, '__code__')
                for func_name in cls.__safe_dir(module)
                for func in [cls.__safe_getattr(module, func_name)]
                if cls.__safe_isinstance(func, types.FunctionType)
                and cls.__safe_getattr(func, '__code__') is not None
            )

            # Collect code objects from class methods
            code_objects.update(
                cls.__safe_getattr(method, '__code__')
                for cls_name in cls.__safe_dir(module)
                for cls_attr in [cls.__safe_getattr(module, cls_name)]
                if cls.__safe_isinstance(cls_attr, type)
                for attr_name in cls.__safe_dir(cls_attr)
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
    def __safe_hasattr(cls, obj, attr: str) -> bool:
        """
        Safely checks if an object has an attribute without triggering side effects.
        """
        try:
            cls.__safe_getattr(obj, attr)
            return True
        except BaseException:
            return False

    @classmethod
    def __get_src_info(cls, obj) -> Dict:
        """
        Retrieves source information (filename, line number, function name) of the object.
        """
        try:
            if cls.__safe_isinstance(obj, (types.FunctionType, types.MethodType)):
                code = cls.__safe_getattr(obj, '__code__')
                src_info = {key: value for key, value in {
                    'co_name': cls.__safe_getattr(code, 'co_name'),
                    'co_filename': cls.__safe_getattr(code, 'co_filename'),
                    'co_lineno': cls.__safe_getattr(code, 'co_firstlineno')
                }.items() if value is not None}

            elif cls.__safe_isinstance(obj, (type, types.ModuleType)):
                src_info = {key: value for key, value in {
                    'co_name': cls.__safe_getattr(obj, '__name__'),
                    'co_filename': cls.__safe_getattr(obj, '__file__'),
                }.items() if value is not None}

            else:
                cls_obj = cls.__safe_getattr(obj, '__class__')
                if cls_obj is not None:
                    init_method = cls.__safe_getattr(cls_obj, '__init__')
                    code = cls.__safe_getattr(init_method, '__code__') if init_method else None

                    cls_name = cls.__safe_getattr(cls_obj, '__name__')
                    cls_module = cls.__safe_getattr(cls_obj, '__module__')
                    module_obj = sys.modules.get(cls_module) if cls_module else None
                    module_file = cls.__safe_getattr(module_obj, '__file__') if module_obj else None

                    src_info = {key: value for key, value in {
                        'co_name': cls.__safe_getattr(code, 'co_name') if code else cls_name,
                        'co_filename': cls.__safe_getattr(code, 'co_filename') if code else module_file,
                        'co_lineno': cls.__safe_getattr(code, 'co_firstlineno') if code else None
                    }.items() if value is not None}
                else:
                    src_info = {}

            return src_info
        except BaseException:
            return {}

    @classmethod
    def __convert_value(cls, value) -> Any:
        """
        Converts a value to a JSON-serializable format.
        """
        if value is None:
            return None
        if cls.__safe_isinstance(value, (bool, int)):
            return value

        if cls.__safe_isinstance(value, float):
            try:
                return value if math.isfinite(value) else str(value)
            except BaseException:
                return str(value)

        if cls.__safe_isinstance(value, str):
            try:
                return value[:1000]
            except BaseException:
                return "[STRING_ACCESS_ERROR]"

        if cls.__safe_isinstance(value, (bytes, memoryview)):
            try:
                return str(value[:1000])
            except BaseException:
                return "[BYTES_ACCESS_ERROR]"

        if cls.__safe_isinstance(value, (Decimal, Fraction, complex)):
            try:
                return str(value)
            except BaseException:
                return "[NUMBER_CONVERT_ERROR]"

        if cls.__safe_isinstance(value, range):
            try:
                return str(list(value)[:1000])
            except BaseException:
                return "[RANGE_CONVERT_ERROR]"

        try:
            return [str(type(value)), id(value)]
        except BaseException:
            return ["[UNKNOWN_TYPE]", 0]

    @classmethod
    def __get_object_metadata(cls, obj) -> Dict:
        """
        Collects metadata for a specific object, including its size, attributes,
        references, and source code information.
        """
        try:
            obj_metadata: Any = {'size': sys.getsizeof(obj)}
        except BaseException:
            obj_metadata = {'size': 0}

        # Collect attributes using safe dir() + getattr()
        try:
            attrs = {
                attr_name: cls.__convert_value(attr_value)
                for attr_name in cls.__safe_dir(obj)
                if not (attr_name.startswith('__') and attr_name.endswith('__'))
                for attr_value in [cls.__safe_getattr(obj, attr_name)]
                if attr_value is not None
            }
            if attrs:
                obj_metadata['attr'] = attrs
        except BaseException:
            pass

        # Collect references using gc.get_referents() for all types
        try:
            references = gc.get_referents(obj)
            if references:
                obj_metadata['ref'] = [cls.__convert_value(ref) for ref in references]
        except BaseException:
            pass

        # Collect source info
        src_info: Any = cls.__get_src_info(obj)
        if src_info:
            obj_metadata['src'] = src_info

        return obj_metadata
