import pathlib
import os
import sys
import tempfile
import time
import traceback

# Ép mã hóa UTF-8 cho console, nếu không thì tiếng Việt sẽ lỗi trên Windows
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from model.Configuration import Configuration
from algorithm.GeneticAlgorithm import GeneticAlgorithm
# from algorithm.APNsgaIII import APNsgaIII
# from algorithm.Cso import Cso
# from algorithm.GaQpso import GaQpso
# from algorithm.Amga2 import Amga2
from HtmlOutput import HtmlOutput
from Trace import Trace as Tracer


def main(file_name):
    start_time = int(round(time.time() * 1000))

    configuration = Configuration()
    target_file = str(pathlib.Path().absolute()) + file_name
    configuration.parseFile(target_file)

    # In toàn bộ thông tin đầu vào trước khi chạy thuật toán
    Tracer.input(configuration, file_name)

    alg = GeneticAlgorithm(configuration)
    # alg = GaQpso(configuration)
    print("GaSchedule phiên bản 1.2.6. Lập thời khóa biểu bằng", alg, ".\n")
    print("Bản quyền (C) 2022 - 2024 Miller Cy Chan.\n")
    Tracer.reset()
    alg.run()
    html_result = HtmlOutput.getResult(alg.result, history=Tracer.get_history())

    temp_file_path = tempfile.gettempdir() + file_name.replace(".json", ".htm")
    with open(temp_file_path, "w", encoding="utf-8") as writer:
        writer.write(html_result)

    seconds = (int(round(time.time() * 1000)) - start_time) / 1000.0
    print("\nHoàn thành trong {} giây.\n".format(seconds))
    os.startfile(temp_file_path)


if __name__ == "__main__":
    file_name = "/GaSchedule.json"
    if len(sys.argv) > 1:
        file_name = sys.argv[1]

    try:
        main(file_name)
    except:
        traceback.print_exc()
