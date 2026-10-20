from model.Schedule import Schedule
import numpy as np
import random
import sys
from time import time
from Trace import Trace


# K.Deb, A.Pratap, S.Agrawal, T.Meyarivan, A fast and elitist multiobjective genetic algorithm: 
# NSGA-II, IEEE Transactions on Evolutionary Computation 6 (2002) 182–197.
# Copyright (c) 2020 - 2022 Miller Cy Chan


# NSGA II
class NsgaII:
    def initAlgorithm(self, prototype, numberOfChromosomes=100):
        # Nhiễm sắc thể mẫu (prototype) của quần thể
        self._prototype = prototype

        # quần thể phải có ít nhất 2 nhiễm sắc thể
        if numberOfChromosomes < 2:
            numberOfChromosomes = 2

        # Quần thể nhiễm sắc thể
        self._chromosomes = []
        self._populationSize = numberOfChromosomes
        self._repeatRatio = .0

    # Khởi tạo thuật toán di truyền
    def __init__(self, configuration, numberOfCrossoverPoints=2, mutationSize=2, crossoverProbability=80,
                 mutationProbability=3):
        self.initAlgorithm(Schedule(configuration))
        self._mutationSize = mutationSize
        self._numberOfCrossoverPoints = numberOfCrossoverPoints
        self._crossoverProbability = crossoverProbability
        self._mutationProbability = mutationProbability

    @property
    # Trả về con trỏ tới các nhiễm sắc thể tốt nhất trong quần thể
    def result(self):
        return self._chromosomes[0]

    # hàm sắp xếp theo thứ bậc phi thống trội (non-dominated sorting)
    def nonDominatedSorting(self, totalChromosome):
        doublePopulationSize = self._populationSize * 2
        s = doublePopulationSize * [ set() ]
        n = np.zeros(doublePopulationSize, dtype=int)
        front = [ set() ]

        for p in range(doublePopulationSize):
            for q in range(doublePopulationSize):
                if totalChromosome[p].fitness > totalChromosome[q].fitness:
                    s[p].add(q)
                elif totalChromosome[p].fitness < totalChromosome[q].fitness:
                    n[p] += 1

            if n[p] == 0:
                front[0].add(p)
    
        i = 0
        while front[i]:
            Q = set()
            for p in front[i]:
                for q in s[p]:
                    n[q] -= 1
                    if n[q] == 0:
                        Q.add(q)
            i += 1
            front.append(Q)

        front.pop()
        return front

    # hàm tính khoảng cách chen chúc (crowding distance)
    def calculateCrowdingDistance(self, front, totalChromosome):
        distance, obj = {}, {}
        for key in front:
            distance[key] = 0
            fitness = totalChromosome[key].fitness
            if fitness not in obj.values():
                obj[key] = fitness

        sorted_keys = sorted(obj, key=obj.get)
        size = len(obj)
        distance[sorted_keys[0]] = distance[sorted_keys[-1]] = sys.float_info.max
        
        if size > 1:
            diff2 = totalChromosome[sorted_keys[-1]].getDifference(totalChromosome[sorted_keys[0]])
                
            for i in range(1, size - 1):
                diff = totalChromosome[sorted_keys[i + 1]].getDifference(totalChromosome[sorted_keys[i - 1]]) / diff2
                distance[sorted_keys[i]] += diff

        return distance

    def selection(self, front, totalChromosome):
        populationSize = self._populationSize
        calculateCrowdingDistance = self.calculateCrowdingDistance
        N = 0
        newPop = []
        while N < populationSize:
            for row in front:
                N += len(row)
                if N > populationSize:
                    distance = calculateCrowdingDistance(row, totalChromosome)
                    sortedCdf = sorted(distance, key=distance.get, reverse=True)
                    for j in sortedCdf:
                        if len(newPop) >= populationSize:
                            break
                        newPop.append(j)
                    break
                newPop.extend(row)
    
        return [totalChromosome[n] for n in newPop]

    def replacement(self, population):
        populationSize = self._populationSize
        numberOfCrossoverPoints = self._numberOfCrossoverPoints
        crossoverProbability = self._crossoverProbability
        offspring = []
        # sinh một dãy ngẫu nhiên để chọn nhiễm sắc thể cha mẹ cho việc lai ghép
        S = np.arange(populationSize)
        np.random.shuffle(S)

        halfPopulationSize = populationSize // 2
        for m in range(halfPopulationSize):
            parent0 = population[S[2 * m]]
            parent1 = population[S[2 * m + 1]]
            child0 = parent0.crossover(parent1, numberOfCrossoverPoints, crossoverProbability)
            child1 = parent1.crossover(parent0, numberOfCrossoverPoints, crossoverProbability)

            # thêm nhiễm sắc thể con vào danh sách con cái
            offspring.extend((child0, child1))
            
        return offspring
                
    # khởi tạo quần thể mới với các nhiễm sắc thể được sinh ngẫu nhiên từ nhiễm sắc thể mẫu
    def initialize(self, population):
        prototype = self._prototype

        for i in range(len(population)):
            # thêm nhiễm sắc thể mới vào quần thể
            population[i] = prototype.makeNewFromPrototype()

    def reform(self):
        random.seed(round(time() * 1000))
        np.random.seed(int(time()))
        if self._crossoverProbability < 95:
            self._crossoverProbability += 1.0
        elif self._mutationProbability < 30:
            self._mutationProbability += 1.0

    # Bắt đầu và thực thi thuật toán
    def run(self, maxRepeat=9999, minFitness=0.999):
        mutationSize = self._mutationSize
        mutationProbability = self._mutationProbability
        nonDominatedSorting = self.nonDominatedSorting
        selection = self.selection
        populationSize = self._populationSize
        population = populationSize * [None]

        self.initialize(population)
        random.seed(round(time() * 1000))
        np.random.seed(int(time()))

        # Thế hệ hiện tại
        currentGeneration = 0

        repeat = 0
        lastBestFit = 0.0

        while 1:
            if currentGeneration > 0:
                best = self.result

                # thuật toán đã đạt tiêu chí?
                if best.fitness > minFitness:
                    break

                difference = abs(best.fitness - lastBestFit)
                if difference <= 0.0000001:
                    repeat += 1
                else:
                    repeat = 0

                self._repeatRatio = repeat * 100 / maxRepeat
                if repeat > (maxRepeat / 100):
                    self.reform()

            # lai ghép (crossover)
            offspring = self.replacement(population)

            # đột biến (mutation)
            for child in offspring:
                child.mutation(mutationSize, mutationProbability)

            totalChromosome = population + offspring

            # Sắp xếp theo thứ bậc phi thống trội (non-dominated sorting)
            front = nonDominatedSorting(totalChromosome)
            if len(front) == 0:
                break

            # chọn lọc (selection)
            population = selection(front, totalChromosome)
            self._populationSize = populationSize = len(population)

            # so sánh (comparison)
            if currentGeneration == 0:
                self._chromosomes = population
            else:
                totalChromosome = population + self._chromosomes
                newBestFront = nonDominatedSorting(totalChromosome)
                if len(newBestFront) == 0:
                    break
                self._chromosomes = selection(newBestFront, totalChromosome)
                lastBestFit = best.fitness

            Trace.trace(self, currentGeneration + 1, repeat)
            currentGeneration += 1
            
    def __str__(self):
        return "NSGA II"
