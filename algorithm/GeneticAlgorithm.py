from model.Schedule import Schedule
import random
from random import randrange
from time import time
from Trace import Trace


# Lakshmi, R. et al. “A New Biological Operator in Genetic Algorithm for Class Scheduling Problem.” 
# International Journal of Computer Applications 60 (2012): 6-11.
# Copyright (c) 2020 - 2022 Miller Cy Chan


# Thuật toán di truyền (Genetic Algorithm)
class GeneticAlgorithm:
    def initAlgorithm(self, prototype, numberOfChromosomes=100, replaceByGeneration=8, trackBest=5):
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

        # Chỉ số của các nhiễm sắc thể tốt nhất
        self._bestChromosomes = trackBest * [0]
        # Số nhiễm sắc thể bị thay thế bởi con cái trong mỗi thế hệ
        self.set_replace_by_generation(replaceByGeneration)

    # Khởi tạo thuật toán di truyền
    def __init__(self, configuration, numberOfCrossoverPoints=2, mutationSize=2, crossoverProbability=80,
                 mutationProbability=3, maxIterations=1000, maxStagnation=100,
                 numberOfChromosomes=100, replaceByGeneration=8, trackBest=5):
        self.initAlgorithm(
            Schedule(configuration),
            numberOfChromosomes,
            replaceByGeneration,
            trackBest,
        )
        self._mutationSize = max(1, int(mutationSize))
        self._numberOfCrossoverPoints = max(1, int(numberOfCrossoverPoints))
        self._crossoverProbability = max(0, min(100, int(crossoverProbability)))
        self._mutationProbability = max(0, min(100, int(mutationProbability)))

        # Số thế hệ tối đa thuật toán được phép chạy (có thể ghi đè khi gọi run)
        self._max_iterations = max(1, maxIterations)
        # Dừng nếu fitness không cải thiện trong liên tiếp maxStagnation thế hệ
        # (có thể ghi đè khi gọi run)
        self._max_stagnation = max(1, maxStagnation)

    @property
    # Trả về con trỏ tới các nhiễm sắc thể tốt nhất trong quần thể
    def result(self):
        return self._chromosomes[self._bestChromosomes[0]]

    def set_replace_by_generation(self, value):
        numberOfChromosomes = len(self._chromosomes)
        trackBest = len(self._bestChromosomes)
        value = max(1, int(value))
        if (value > numberOfChromosomes - trackBest):
            value = numberOfChromosomes - trackBest
        self._replaceByGeneration = value

    # Cố gắng thêm nhiễm sắc thể vào nhóm nhiễm sắc thể tốt nhất
    def addToBest(self, chromosomeIndex):
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

    # Xóa nhóm nhiễm sắc thể tốt nhất
    def clearBest(self):
        self._bestFlags = len(self._bestFlags) * [False]
        self._currentBestSize = 0

    # khởi tạo quần thể mới với các nhiễm sắc thể được sinh ngẫu nhiên từ nhiễm sắc thể mẫu
    def initialize(self, population):
        # addToBest = self.addToBest
        prototype = self._prototype
        length_chromosomes = len(population)

        for i in range(0, length_chromosomes):
            # thêm nhiễm sắc thể mới vào quần thể
            population[i] = prototype.makeNewFromPrototype()
            # addToBest(i)

    def selection(self, population):
        length_chromosomes = len(population)
        return (population[randrange(32768) % length_chromosomes],  population[randrange(32768) % length_chromosomes])

    def replacement(self, population, replaceByGeneration) -> []:
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

            offspring[j] = parent[0].crossover(parent[1], numberOfCrossoverPoints, crossoverProbability)
            offspring[j].mutation(mutationSize, mutationProbability)

            # thay thế các nhiễm sắc thể của lượt chạy hiện tại bằng con cái
            # chọn ngẫu nhiên nhiễm sắc thể để thay thế
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
        # Cho phép ghi đè cấu hình mặc định khi gọi run()
        maxIterations = self._max_iterations if maxIterations is None else max(1, maxIterations)
        maxStagnation = self._max_stagnation if maxStagnation is None else max(1, maxStagnation)

        # xóa nhóm nhiễm sắc thể tốt nhất từ lần chạy trước
        self.clearBest()
        length_chromosomes = len(self._chromosomes)

        self.initialize(self._chromosomes)
        random.seed(round(time() * 1000))

        # Thế hệ hiện tại
        currentGeneration = 0

        repeat = 0
        lastBestFit = 0.0

        while currentGeneration < maxIterations:
            best = self.result

            # thuật toán đã đạt tiêu chí?
            if best.fitness > minFitness:
                break

            difference = abs(best.fitness - lastBestFit)
            if difference <= 0.0000001:
                repeat += 1
            else:
                repeat = 0

            # dừng nếu fitness không cải thiện trong maxStagnation thế hệ liên tiếp
            if repeat >= maxStagnation:
                break

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
