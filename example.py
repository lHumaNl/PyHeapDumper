import os.path
import time
import logging
from heap_dumper import HeapDumper


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')  # Configure logging
    file_dir = os.path.join('heap_dumps', 'examples')  # Forming heap dump files dir
    some_production_activity(file_dir)


def do_some_work():
    """Simulates some work being done in a loop."""
    result = 0
    for i in range(1000000):
        result += i ** 0.5  # Simple operation for workload


def some_production_activity(file_dir: str):
    """
    Creates heap dumps at a specified interval for a given duration.

    Args:
        file_dir (str): The name of the dir where heap dumps will be saved.
    """
    counter = 0
    while True:
        do_some_work()  # Perform background work
        file_name = os.path.join(file_dir, f'heap_dump_{counter}')  # Forming file name

        try:
            logging.info(
                HeapDumper.collect_heap_metadata(file_name)  # Take heap dump and send success message to logger
            )
        except Exception as e:
            logging.error(e)  # Send exception message with traceback to logger

        counter += 1
        time.sleep(10)  # Wait before the next heap dump


if __name__ == "__main__":
    main()  # Run application
