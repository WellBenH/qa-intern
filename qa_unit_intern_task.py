# encoding: utf-8

"""
task: qa-unit-intern-task + jsonschema check + docker
date: 16.05.19
author: Fomichev V
docker_url: 2653/qa_intern
"""

import os
import json
from jsonschema import validate, exceptions as je
from datetime import datetime
from time import gmtime, strftime

need_to_check_schemas = True

direct_to_json = os.path.join(os.curdir, 'json_files')
direct_with_result = os.path.join(os.curdir, 'results')
direct_with_schemas = os.path.join(os.curdir, 'schemas')
utc_offset = datetime.now().timestamp() - datetime.utcnow().timestamp()
utc_offset += 1 if os.name != 'nt' else 0


def json_validate(schema_type, json_data):

    schemas = {
        'logs': 'log_schema.json',
        'suites': 'suites_schema.json',
        'captures': 'captures_schema.json'
    }

    if os.path.exists(os.path.join(direct_with_schemas, schemas[schema_type])):
        with open(os.path.join(direct_with_schemas, schemas[schema_type])) as j_schema:
            try:
                schema = json.load(j_schema)
                validate(json_data, schema)
                return 1
            except (je.SchemaError, je.ValidationError, json.decoder.JSONDecodeError):
                return 0


def get_data_from_json_files():
    result = {}

    def get_logs_result(logs):
        for log in logs["logs"]:
            try:
                yield {int(log.pop("time")): log}
            except (KeyError, ValueError):
                continue

    def get_suites_result(suites):
        for suite in suites["suites"]:
            try:
                for case in suite["cases"]:
                    yield {
                        int(datetime.strptime(
                            case.pop("time"), "%A, %d-%b-%y %H:%M:%S %Z").timestamp()+utc_offset): case
                    }
            except (KeyError, TypeError, ValueError):
                continue

    def get_captures_result(captures):
        for capture in captures["captures"]:
            try:
                yield {int(datetime.strptime(capture.pop("time"),
                                             "%Y-%m-%dT%H:%M:%S%z").timestamp()): capture}
            except (KeyError, TypeError, ValueError):
                continue

    if not os.path.exists(direct_to_json):
        return []

    for json_file in (os.path.join(direct_to_json, file)
                      for file in os.listdir(direct_to_json) if file.endswith('.json')):
        try:
            with open(json_file) as jf:
                raw_data = json.load(jf)
                for type_key, func in zip(
                        ('logs', 'suites', 'captures'),
                        (get_logs_result, get_suites_result, get_captures_result)
                ):
                    if not raw_data.get(type_key):
                        continue
                    if need_to_check_schemas and not json_validate(type_key, raw_data):
                        continue
                    for item in func(raw_data):
                        for key, value in item.items():
                            if result.get(key):
                                result[key].update(value)
                            else:
                                result.update({key: value})
                    break
        except json.decoder.JSONDecodeError:
            continue

    return result


def get_data_for_result_json_file(raw_result):
    name_dict = {
        'name': 'test_name',
        'test': 'test_name',
        'output': 'test_status',
        'errors': 'test_status',
        'expected': 'expected_result',
        'actual': 'actual_result'
    }
    result_names = set(name_dict.values())
    result = {"results": []}
    for data in raw_result.values():
        local = {}
        for field, value in data.items():
            field_name = name_dict.get(field)
            if not field_name:
                continue
            if field_name is 'test_status' and type(value) == int:
                value = 'fail' if value else 'success'
            local.update({field_name: value})

        success_counter = 0

        for exp_name in result_names:
            if exp_name in local.keys():
                success_counter += 1

        if success_counter == len(result_names):
            result["results"].append(local)

    return result


def save_result(result):
    os.makedirs(direct_with_result, exist_ok=True)
    file_name = strftime('%Y%m%d%H%M%S', gmtime()) + '_join_result.json'
    with open(os.path.join(direct_with_result, file_name), 'w') as jr:
        json.dump(result, jr, indent=4)
    return file_name


def main():
    raw_result = get_data_from_json_files()
    print('No one group created by keys!') if not raw_result else\
        print('Group created by key: {}'.format(len(raw_result)))
    if not raw_result:
        return
    result = get_data_for_result_json_file(raw_result) if raw_result else None
    print('No one complete object was created!') if not result['results'] else \
        print('Total created objects: {}'.format(len(result['results'])))
    if not result['results']:
        return
    result_file_name = save_result(result) if result['results'] else None
    print('Results saved to file {}'.format(result_file_name)) if result_file_name\
        else print('No results were saved!')


if __name__ == '__main__':
    main()
