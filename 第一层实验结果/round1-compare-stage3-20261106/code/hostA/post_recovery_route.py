"""Choose original-order verification when LS finished before its wrapper timed out."""
import json
from pathlib import Path


def completed_ls_original_order_available(directory):
    directory = Path(directory)
    order = directory / 'order.json'
    checkpoint = directory / 'last-completed-sweep.checkpoint.json'
    if not order.is_file() or not checkpoint.is_file():
        return False
    record = directory / 'record.json'
    if record.is_file() and json.loads(record.read_text()).get('order_path'):
        return False
    history = json.loads(checkpoint.read_text()).get('history') or []
    return bool(history and (len(history) == 10 or history[-1].get('accepted') == 0))
