# PyHeapDumper

This project provides a utility to create heap dumps of Python objects and save them in JSON format. The main component
is the `HeapDumper` class, which collects metadata of objects in memory and stores them in a file. A sample usage
script (`example.py`) demonstrates how to periodically take heap dumps while performing background operations.

# Profiling heap dumps

For profiling captured heap dumps use this util: https://github.com/lHumaNl/PyHeapProfiler

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
    - [HeapDumper Class](#heapdumper-class)
    - [Example Script](#example-script)

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard Python libraries)

## Installation

1. Clone this repository:
    ```bash
    git clone https://github.com/lHumaNl/PyHeapDumper.git
    ```

2. Place the `heap_dumper.py` file into your project, and import the `HeapDumper` class or specific methods into the
   part of your code where you want to collect heap dumps. For example usage, see the `example.py` file.

   Example import:
    ```bash
    from heap_dumper import HeapDumper
    ```

   Then, call `HeapDumper.collect_heap_metadata` wherever you need to capture the heap dump.

## Usage

### HeapDumper Class

The `HeapDumper` class is responsible for collecting metadata from objects currently in memory and saving it as a JSON
file.

#### Methods:

- **`collect_heap_metadata(file_name: str) -> str`**:
  This method collects metadata for all objects currently in memory, including additional code objects. It then saves
  the heap dump to the specified `file_name`. It returns a string message indicating the success or Exception with fail
  message and traceback.

- **Private methods**:
    - `__safe_getattr`: Safely retrieve an attribute from an object.
    - `__safe_isinstance`: Safely check if an object is an instance of a given type.
    - `__get_code_objects`: Collect all code objects currently loaded in memory.
    - `__save_heap_dump`: Save the heap dump to a JSON file.
    - `__get_src_info`: Retrieve source information (filename, line number, etc.) from an object.
    - `__get_object_metadata`: Collect detailed metadata from a specific object, including its size, attributes, and
      references.

### Example Script

The `example.py` script demonstrates how to periodically take heap dumps while some background work is being performed.

#### Running the example:

To run the example:

```bash
python example.py
```

### This will:

Perform some simple calculations in the background.
Take a heap dump every 10 seconds and save it to ./heap_dumps/examples/heap_dump_count.json.