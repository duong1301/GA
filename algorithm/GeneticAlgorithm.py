"""Vòng tiến hoá của giải thuật di truyền dùng để xếp thời khoá biểu.

Một cá thể (nhiễm sắc thể) là một phương án xếp lịch hoàn chỉnh; xem
model/Schedule.py để biết cách mã hoá và cách tính độ phù hợp.

QUY TRÌNH MỖI THẾ HỆ (run -> replacement):
  1. selection: rút ngẫu nhiên đều 2 cá thể làm cha mẹ.
  2. crossover: con nhận gen (ngày, phòng, tiết) và giảng viên của từng lớp
     từ một trong hai cha mẹ, đổi nguồn tại các điểm lai ghép.
  3. mutation: dời tối đa mutationSize lớp sang ô ngẫu nhiên, gán lại giảng viên.
  4. replacement: con lai thay một cá thể ngẫu nhiên KHÔNG thuộc nhóm tốt nhất,
     nên cá thể elit luôn sống sót (elitism).
  5. Trace.trace: in và lưu ảnh chụp thế hệ; lỗi theo dõi không được làm hỏng
     vòng chạy.

TIÊU CHÍ DỪNG (trong run):
  - best.fitness > minFitness        : đạt mục tiêu, dừng sớm.
  - currentGeneration >= maxIterations: hết ngân sách thế hệ.
  - repeat >= maxStagnation          : fitness tốt nhất đứng yên (|Δ| <= 1e-7)
                                       trong maxStagnation thế hệ liên tiếp.

Tài liệu tham khảo của bộ toán tử:
Lakshmi, R. et al. "A New Biological Operator in Genetic Algorithm for Class
Scheduling Problem." International Journal of Computer Applications 60 (2012): 6-11.
Copyright (c) 2020 - 2022 Miller Cy Chan
"""
from model.Schedule import Schedule
import random
from random import randrange
from time import time
from Trace import Trace


# Thuật toán di truyền (Genetic Algorithm)
class GeneticAlgorithm:
    # Bất biến của nhóm tốt nhất (elitelist): các chỉ số trong _bestChromosomes
    # được sắp theo fitness GIẢM DẦN, nên _bestChromosomes[0] luôn là cá thể tốt
    # nhất toàn quần thể và _bestFlags đánh dấu đúng các chỉ số đó.
    def initAlgorithm(self, prototype, numberOfChromosomes=100, replaceByGeneration=8, trackBest=5):
        """Dựng khung quần thể rỗng và nhóm elit cho trước (chưa sinh cá thể).

        Các ngưỡng dưới đây bảo đảm mọi chỉ số dùng sau này đều hợp lệ:
          N = numberOfChromosomes >= 2
          1 <= trackBest <= N - 1        (luôn còn ít nhất 1 chỗ cho con lai)
          1 <= replaceByGeneration <= N - trackBest  (xem set_replace_by_generation)
        """
        # Số nhiễm sắc thể tốt nhất hiện được lưu trong nhóm nhiễm sắc thể tốt nhất
        self._currentBestSize = 0
        # Nhiễm sắc thể mẫu (prototype) của quần thể
        self._prototype = prototype

        # quần thể phải có ít nhất 2 nhiễm sắc thể
        numberOfChromosomes = max(2, int(numberOfChromosomes))

        # phải theo dõi ít nhất một nhiễm sắc thể tốt nhất,
        # nhưng vẫn phải chừa chỗ cho ít nhất một nhiễm sắc thể con
        trackBest = min(max(1, int(trackBest)), numberOfChromosomes - 1)

        # Quần thể nhiễm sắc thể
        self._chromosomes = numberOfChromosomes * [None]
        # Cho biết nhiễm sắc thể có thuộc nhóm nhiễm sắc thể tốt nhất hay không
        self._bestFlags = numberOfChromosomes * [False]

        # Chỉ số của các nhiễm sắc thể tốt nhất (mảng đã sắp theo fitness giảm dần,
        # khởi tạo toàn 0 vì quần thể còn trống)
        self._bestChromosomes = trackBest * [0]
        # Số nhiễm sắc thể bị thay thế bởi con cái trong mỗi thế hệ
        self.set_replace_by_generation(replaceByGeneration)

    # Khởi tạo thuật toán di truyền
    def __init__(self, configuration, numberOfCrossoverPoints=2, mutationSize=2, crossoverProbability=80,
                 mutationProbability=3, maxIterations=1000, maxStagnation=100,
                 numberOfChromosomes=100, replaceByGeneration=8, trackBest=5):
        # Prototype chỉ mang cấu hình (số lớp, số phòng, giảng viên...), không
        # mang gen; initialize() sẽ nhân bản nó thành N cá thể ngẫu nhiên.
        self.initAlgorithm(
            Schedule(configuration),
            numberOfChromosomes,
            replaceByGeneration,
            trackBest,
        )
        # Số lớp bị dời trong MỘT lần đột biến (đột biến vẫn có thể trùng lớp).
        self._mutationSize = max(1, int(mutationSize))
        # Số điểm cắt khi lai ghép; Schedule.crossover tự giới hạn theo số lớp.
        self._numberOfCrossoverPoints = max(1, int(numberOfCrossoverPoints))
        # Ngưỡng phần trăm (0-100) cho hai phép thử xác suất ở dưới; xem
        # Schedule.crossover và Schedule.mutation để biết xác suất thực sự là
        # (p + 1) / 100 vì randrange(100) trả 0..99.
        self._crossoverProbability = max(0, min(100, int(crossoverProbability)))
        self._mutationProbability = max(0, min(100, int(mutationProbability)))

        # Số thế hệ tối đa thuật toán được phép chạy (có thể ghi đè khi gọi run)
        self._max_iterations = max(1, maxIterations)
        # Dừng nếu fitness không cải thiện trong liên tiếp maxStagnation thế hệ
        # (có thể ghi đè khi gọi run)
        self._max_stagnation = max(1, maxStagnation)

    @property
    # Trả về con trỏ tới cá thể tốt nhất hiện có (phần tử đầu của elitelist,
    # nhờ bất biến "sắp theo fitness giảm dần" ở đầu lớp).
    # Trước lần addToBest đầu tiên, elitelist còn toàn 0 nên đây chính là cá thể
    # ngẫu nhiên thứ nhất của quần thể.
    def result(self):
        return self._chromosomes[self._bestChromosomes[0]]

    def set_replace_by_generation(self, value):
        """Ép số con lai mỗi thế hệ vào khoảng [1, N - trackBest].

        Hiệu (N - trackBest) là số chỗ không bị elit chiếm, nhờ vậy con lai luôn
        còn chỗ đứng và elit không bao giờ bị ghi đè.
        """
        numberOfChromosomes = len(self._chromosomes)
        trackBest = len(self._bestChromosomes)
        value = max(1, int(value))
        if (value > numberOfChromosomes - trackBest):
            value = numberOfChromosomes - trackBest
        self._replaceByGeneration = value

    # Cố gắng thêm nhiễm sắc thể vào nhóm nhiễm sắc thể tốt nhất
    def addToBest(self, chromosomeIndex):
        """Chèn cá thể vào elitelist theo thứ tự fitness giảm dần (O(trackBest)).

        Hai trường hợp từ bỏ ngay:
          - nhóm đã đầy VÀ cá thể mới không tốt hơn phần tử cuối nhóm (đứng thứ
            trackBest - 1), vì nó không có cửa lọt vào top;
          - cá thể đã nằm trong nhóm.
        Khi nhóm đầy, phần tử cuối (kém nhất) bị kéo ra khỏi _bestFlags để
        nhường chỗ.
        """
        bestChromosomes = self._bestChromosomes
        length_best = len(bestChromosomes)
        bestFlags = self._bestFlags
        chromosomes = self._chromosomes

        # không thêm nếu nhiễm sắc thể mới chưa có độ thích nghi đủ lớn cho nhóm nhiễm sắc thể tốt nhất
        # hoặc nó đã nằm trong nhóm đó?
        if (self._currentBestSize == length_best and chromosomes[bestChromosomes[self._currentBestSize - 1]].fitness >=
            chromosomes[chromosomeIndex].fitness) or bestFlags[chromosomeIndex]:
            return

        # tìm vị trí cho nhiễm sắc thể mới
        i = self._currentBestSize
        while i > 0:
            pos = bestChromosomes[i - 1]
            # nhóm chưa đầy?
            if i < length_best:
                # đã tìm được vị trí của nhiễm sắc thể mới?
                if chromosomes[pos].fitness > chromosomes[chromosomeIndex].fitness:
                    break

                # dời các nhiễm sắc thể để nhường chỗ cho nhiễm sắc thể mới
                bestChromosomes[i] = pos
            else:
                # nhóm đã đầy, loại bỏ các nhiễm sắc thể tệ nhất trong nhóm
                bestFlags[pos] = False
            i -= 1

        # lưu nhiễm sắc thể vào nhóm nhiễm sắc thể tốt nhất
        bestChromosomes[i] = chromosomeIndex
        bestFlags[chromosomeIndex] = True

        # tăng kích thước hiện tại nếu chưa đạt tới giới hạn
        if self._currentBestSize < length_best:
            self._currentBestSize += 1

    # Trả về TRUE nếu nhiễm sắc thể thuộc nhóm nhiễm sắc thể tốt nhất
    def isInBest(self, chromosomeIndex) -> bool:
        return self._bestFlags[chromosomeIndex]

    # Xóa nhóm nhiễm sắc thể tốt nhất (gọi đầu mỗi lần run để elitelist không
    # giữ chỉ số của quần thể cũ)
    def clearBest(self):
        self._bestFlags = len(self._bestFlags) * [False]
        self._currentBestSize = 0

    # khởi tạo quần thể mới với các nhiễm sắc thể được sinh ngẫu nhiên từ nhiễm sắc thể mẫu
    def initialize(self, population):
        """Sinh N cá thể ban đầu, mỗi cá thể tự tính fitness khi tạo ra.

        Quần thể khởi tạo KHÔNG được đưa vào elitelist (addToBest bị chú thích ở
        trên): các chỉ số elit chỉ được nạp dần trong replacement của thế hệ 0.
        """
        prototype = self._prototype
        length_chromosomes = len(population)

        for i in range(0, length_chromosomes):
            # thêm nhiễm sắc thể mới vào quần thể
            population[i] = prototype.makeNewFromPrototype()

    def selection(self, population):
        """Chọn ngẫu nhiên đều 2 cá thể làm cha mẹ (uniform random pairing).

        Mỗi cá thể có xác suất 1/N như nhau, bất kể fitness: đây không phải
        roulette wheel hay tournament. Áp lực chọn lọc đến từ chỗ elit được bảo
        vệ trong replacement và từ việc con lai phải cạnh tranh fitness.

        randrange(32768) % N lấy số ngẫu nhiên từ Python RNG; khi N không ước số
        của 32768 thì phân phối lệch rất nhỏ (N <= 1000 nên không đáng kể).
        """
        length_chromosomes = len(population)
        return (population[randrange(32768) % length_chromosomes],  population[randrange(32768) % length_chromosomes])

    def replacement(self, population, replaceByGeneration) -> []:
        """Sinh replaceByGeneration con lai và cài chúng vào các chỗ không phải elit.

        Mỗi con lai = crossover(cha, mẹ) rồi mutation, và fitness được tính lại
        bên trong hai toán tử đó. Vị trí bị thay là chỉ số ngẫu nhiên ngoài
        elitelist, nên cá thể tốt nhất không bao giờ mất (elitism); đổi lại quần
        thể chỉ trẻ hoá một phần, phần còn lại giữ nguyên qua các thế hệ.
        """
        mutationSize = self._mutationSize
        numberOfCrossoverPoints = self._numberOfCrossoverPoints
        crossoverProbability = self._crossoverProbability
        mutationProbability = self._mutationProbability
        selection = self.selection
        isInBest = self.isInBest
        length_chromosomes = len(population)
        # sinh ra con cái (offspring)
        offspring = replaceByGeneration * [None]
        for j in range(replaceByGeneration):
            # chọn ngẫu nhiên các nhiễm sắc thể cha mẹ
            parent = selection(population)

            # lai ghép (cha = parent[0], mẹ = parent[1]) rồi đột biến trên con
            offspring[j] = parent[0].crossover(parent[1], numberOfCrossoverPoints, crossoverProbability)
            offspring[j].mutation(mutationSize, mutationProbability)

            # thay thế các nhiễm sắc thể của lượt chạy hiện tại bằng con cái
            # chọn ngẫu nhiên nhiễm sắc thể để thay thế, bỏ qua chỗ của nhóm elit
            ci = randrange(32768) % length_chromosomes
            while isInBest(ci):
                ci = randrange(32768) % length_chromosomes

            # thay thế nhiễm sắc thể
            population[ci] = offspring[j]

            # cố gắng thêm các nhiễm sắc thể mới vào nhóm nhiễm sắc thể tốt nhất
            self.addToBest(ci)
        return offspring


    # Bắt đầu và thực thi thuật toán
    def run(self, maxRepeat=9999, minFitness=0.999, maxIterations=None, maxStagnation=None):
        """Tiến hoá quần thể cho tới khi chạm một trong ba ngưỡng dừng.

        Mỗi vòng lặp là MỘT thế hệ: kiểm tra điều kiện dừng, sinh và cài con lai,
        rồi ghi ảnh chụp qua Trace. Vòng lặp đọc best ở ĐẦU thế hệ nên fitness
        được so sánh/in ra là kết quả của thế hệ trước; riêng Trace đọc lại
        result sau khi cài con lai nên bảng thế hệ phản ánh quần thể mới.
        """
        # Cho phép ghi đè cấu hình mặc định khi gọi run()
        maxIterations = self._max_iterations if maxIterations is None else max(1, maxIterations)
        maxStagnation = self._max_stagnation if maxStagnation is None else max(1, maxStagnation)

        # xóa nhóm nhiễm sắc thể tốt nhất từ lần chạy trước
        self.clearBest()
        length_chromosomes = len(self._chromosomes)

        # thế hệ 0: N cá thể ngẫu nhiên, mỗi cá thể tự tính fitness
        self.initialize(self._chromosomes)
        # Mồi Python RNG theo đồng hồ miligiây. Lưu ý: chỉ các phép thử ở selection
        # và replacement dùng RNG này; Schedule dùng numpy.random nên không chịu
        # ảnh hưởng của random.seed, vì vậy hai lần chạy vẫn khác nhau dù mồi lại.
        random.seed(round(time() * 1000))

        # Thế hệ hiện tại
        currentGeneration = 0

        # Số thế hệ liên tiếp fitness tốt nhất không đổi (bộ đếm stagnation)
        repeat = 0
        # Fitness tốt nhất của thế hệ trước, dùng để phát hiện đứng yên
        lastBestFit = 0.0

        while currentGeneration < maxIterations:
            best = self.result

            # thuật toán đã đạt tiêu chí? So sánh NGHIÊM (fitness > minFitness),
            # nên minFitness = 1.0 chỉ đạt được khi lịch hoàn hảo tuyệt đối.
            if best.fitness > minFitness:
                break

            # công thức stagnation: |Δfitness tốt nhất| <= 1e-7 giữa hai thế hệ
            # liên tiếp được coi là không cải thiện.
            difference = abs(best.fitness - lastBestFit)
            if difference <= 0.0000001:
                repeat += 1
            else:
                repeat = 0

            # dừng nếu fitness không cải thiện trong maxStagnation thế hệ liên tiếp
            if repeat >= maxStagnation:
                break

            # "Mồi nổ" khi quần thể đứng yên quá lâu: mồi lại RNG, nhân ba số
            # con lai mỗi thế hệ (thay máu mạnh hơn, mặc kệ ổn định) và tăng nhẹ
            # xác suất lai ghép.
            # Điều kiện là repeat > maxRepeat / 100, nên với maxRepeat = 9999
            # nhánh này chỉ bật từ repeat = 100 — mà maxStagnation mặc định cũng
            # bằng 100 nên break ở trên đã chặn trước. Hạ maxRepeat xuống dưới
            # 100 × maxStagnation (ví dụ 5000 → bật từ repeat = 51) mới có tác dụng.
            if repeat > (maxRepeat / 100):
                random.seed(round(time() * 1000))
                self.set_replace_by_generation(self._replaceByGeneration * 3)
                self._crossoverProbability += 1

            self.replacement(self._chromosomes, self._replaceByGeneration)

            lastBestFit = best.fitness
            Trace.trace(self, currentGeneration + 1, repeat)
            currentGeneration += 1

    def __str__(self):
        return "Thuật toán di truyền (Genetic Algorithm)"
