# encoding: utf-8

"""
task: qa-unit-intern-task + jsonschema check + docker
date: 16.05.19
docker_url: 2653/qa_intern
git: https://github.com/WellBenH/qa-intern/
"""

import os
import json
from jsonschema import validate, exceptions as je
from datetime import datetime
from time import gmtime, strftime

need_to_check_schemas = True
direct_to_json = os.path.join(os.curdir, 'json_files')  # папка с исходными файлами
direct_with_result = os.path.join(os.curdir, 'results')  # папка в которую сохраняются результаты
direct_with_schemas = os.path.join(os.curdir, 'schemas')  # папка с протатипами схем для jsonschema
utc_offset = datetime.now().timestamp() - datetime.utcnow().timestamp()  # сдвиг для преобразовния даты к GMT+0
utc_offset += 1 if os.name != 'nt' else 0  # небольшой костыль для докера


# Функция для валидации json данных по протатипам схем
def json_validate(schema_type, json_data):

    schemas = {
        'logs': 'log_schema.json',
        'suites': 'suites_schema.json',
        'captures': 'captures_schema.json'
    }

    # Если существует папка с протатипами схем, то открыть и сравнить данные со схемой, которая выбирается по ключу
    if os.path.exists(os.path.join(direct_with_schemas, schemas[schema_type])):
        with open(os.path.join(direct_with_schemas, schemas[schema_type])) as j_schema:
            try:
                schema = json.load(j_schema)
                validate(json_data, schema)
                return 1
            except (je.SchemaError, je.ValidationError, json.decoder.JSONDecodeError):
                return 0


# Сбор сырых данных из файлом с предверительным объединением по ключу
def get_data_from_json_files():
    result = {}

    # обработка результатов из файлов типа logs
    def get_logs_result(logs):
        for log in logs["logs"]:
            try:
                yield {int(log.pop("time")): log}
            except (KeyError, ValueError):
                continue

    # обработка результатов из файлов типа suites, дата приводится к epoch по маске со сдвигом
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

    # обработка результатов из файлов типа captures, дата приводится к epoch по маске
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
                    # если необходимо проверять схемы, но проверка не пройдена, то файл пропускается
                    if need_to_check_schemas and not json_validate(type_key, raw_data):
                        break
                    for item in func(raw_data):
                        for key, value in item.items():
                            if result.get(key):
                                result[key].update(value)  # добавить информацию по ключу
                            else:
                                result.update({key: value})  # создать данные с ключом
                    break
        except json.decoder.JSONDecodeError:
            continue

    return result


#  создание структурны выходных данных из сырых данных
def get_data_for_result_json_file(raw_result):
    name_dict = {
        'name': 'test_name',
        'test': 'test_name',
        'output': 'test_status',
        'errors': 'test_status',
        'expected': 'expected_result',
        'actual': 'actual_result'
    }
    result_names = set(name_dict.values())  # создание списка полей без повторов
    result = {"results": []}
    for data in raw_result.values():
        local = {}
        for field, value in data.items():
            field_name = name_dict.get(field)
            if not field_name:
                continue
            if field_name is 'test_status' and type(value) == int:  # приведение результат в поле test_status
                value = 'fail' if value else 'success'
            local.update({field_name: value})

        success_counter = 0

        #  принятие решения о полноте данных по колличеству полей
        for exp_name in result_names:
            if exp_name in local.keys():
                success_counter += 1

        if success_counter == len(result_names):
            result["results"].append(local)

    return result


# сохранение результата в файл
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
