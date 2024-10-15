import gc
import math
import os
import sys
import json
import traceback
import types
from decimal import Decimal
from fractions import Fraction
from typing import Optional, Any


class HeapDumper:
    @staticmethod
    def __safe_getattr(obj, attr) -> Optional[Any]:
        try:
            return getattr(obj, attr)
        except Exception:
            return None

    @staticmethod
    def __safe_isinstance(obj, types_) -> bool:
        try:
            return isinstance(obj, types_)
        except Exception:
            return False

    @staticmethod
    def collect_heap_metadata(file_name: str) -> str:
        try:
            gc.collect()
            objects = gc.get_objects()

            metadata_dict = {}
            code_objects = set()
            for module in list(sys.modules.values()):
                if module is None:
                    continue

                code_objects.update(
                    HeapDumper.__safe_getattr(func, '__code__')
                    for func_name in dir(module)

                    for func in [HeapDumper.__safe_getattr(module, func_name)]

                    if HeapDumper.__safe_isinstance(func, types.FunctionType)
                    and HeapDumper.__safe_getattr(func, '__code__') is not None
                )

                code_objects.update(
                    HeapDumper.__safe_getattr(method, '__code__')
                    for cls_name in dir(module)
                    for cls in [HeapDumper.__safe_getattr(module, cls_name)]

                    if HeapDumper.__safe_isinstance(cls, type)

                    for attr_name in dir(cls)
                    for method in [HeapDumper.__safe_getattr(cls, attr_name)]

                    if HeapDumper.__safe_isinstance(method, (types.FunctionType, types.MethodType))
                    and HeapDumper.__safe_getattr(method, '__code__') is not None
                )

            code_objects.discard(None)
            objects.extend(code_objects)

            for obj in objects:
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
                        ref if HeapDumper.__safe_isinstance(ref, (int, bool))
                        else (
                            ref if math.isfinite(ref) else str(ref)
                        ) if HeapDumper.__safe_isinstance(ref, float)
                        else ref[:1000] if HeapDumper.__safe_isinstance(ref, str)
                        else str(ref[:1000]) if HeapDumper.__safe_isinstance(ref, (memoryview, bytes))
                        else str(ref) if HeapDumper.__safe_isinstance(ref, (Decimal, Fraction, complex))
                        else str(list(ref)[:1000]) if HeapDumper.__safe_isinstance(ref, range)
                        else None if ref is None
                        else [str(type(ref)), id(ref)]
                        for ref in references
                    ]

                metadata_dict.setdefault(str(type(obj)), {})[id(obj)] = obj_metadata

            dir_name = os.path.dirname(file_name)
            os.makedirs(dir_name, exist_ok=True)

            if not file_name.endswith('.json'):
                file_name += '.json'

            with open(file_name, 'w', encoding='utf-8') as file:
                json.dump(metadata_dict, file, ensure_ascii=False)

            return f'Heap dump "{file_name}" saved!'
        except Exception as e:
            tb = os.linesep.join(traceback.format_exc().split(os.linesep))

            return f'Failed to save heap dump "{file_name}": {e}\n{tb}'
