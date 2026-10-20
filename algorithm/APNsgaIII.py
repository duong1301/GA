from .NsgaIII import NsgaIII
import numpy as np
import random
from time import time
from Trace import Trace


# Wu, M.; Yang, D.; Zhou, B.; Yang, Z.; Liu, T.; Li, L.; Wang, Z.; Hu,
# K. Adaptive Population NSGA-III with Dual Control Strategy for Flexible Job
# Shop Scheduling Problem with the Consideration of Energy Consumption and Weight. Machines 2021, 9, 344.
# https://doi.org/10.3390/machines9120344
# Copyright (c) 2023 Miller Cy Chan


# NSGA-III với quần thể thích ứng và chiến lược điều khiển kép (Adaptive Population NSGA-III with Dual Control Strategy - APNsgaIII)
class APNsgaIII(NsgaIII):
    def __init__(self, configuration, numberOfCrossoverPoints=2, mutationSize=2, crossoverProbability=80,
                 mutationProbability=3, maxIterations=5000):
        self._max_iterations = maxIterations
        self._worst = None
        super().__init__(configuration, numberOfCrossoverPoints, mutationSize, crossoverProbability,
                        mutationProbability)


    def ex(self, chromosome):
        numerator, denominator = 0.0, 0.0
        for f, obj in enumerate(chromosome.objectives):
            numerator += obj - self._best.objectives[f]
            denominator += self._worst.objectives[f] - self._best.objectives[f]

        return (numerator + 1) / (denominator + 1)


    def popDec(self, population):
        N = len(population)
        if N <= self._populationSize:
            return

        rank = int(0.3 * self._populationSize)

        i = 0
        while i < N:
            exValue = self.ex(population[i])

            if exValue > 0.5 and i > rank:
                del population[i]
                N -= 1
                if N <= self._populationSize:
                    break
            i += 1


    def dualCtrlStrategy(self, population, bestNotEnhance, nMax):
        N = len(population)
        nTmp = N
        for i in range(nTmp):
            chromosome = population[i]
            tumor = chromosome.clone()
            tumor.mutation(self._mutationSize, self._mutationProbability)

            self._worst = population[-1]
            if tumor.dominates(chromosome):
                population[i] = tumor
                if tumor.dominates(self._best):
                    self._best = tumor
            else:
                if bestNotEnhance >= 15 and N < nMax:
                    N += 1
                    if self._worst.dominates(tumor):
                        population.append(tumor)
                        self._worst = tumor
                    else:
                        population.insert(-1, tumor)

        self.popDec(population)


    def replacement(self, population):
        result = super().replacement(population)
        result.sort(key = lambda chromosome: chromosome.fitness, reverse=True)
        return result

    # khởi tạo quần thể mới với các nhiễm sắc thể được sinh ngẫu nhiên từ nhiễm sắc thể mẫu
    def initialize(self):
        result = [i for i in map(self.makeNew, range(self._populationSize))]
        return result

    # Bắt đầu và thực thi thuật toán
    def run(self, maxRepeat=9999, minFitness=0.999):
        mutationSize, mutationProbability = self._mutationSize, self._mutationProbability
        populationSize = self._populationSize
        nMax = int(1.5 * populationSize)

        population = self.initialize()

        np.random.seed(int(time()))
        pop = [population, None]

        # Thế hệ hiện tại
        currentGeneration = 0

        bestNotEnhance, lastBestFit = 0, 0.0

        cur, next = 0, 1
        while currentGeneration < self._max_iterations:
            if currentGeneration > 0:
                best = self.result

                # thuật toán đã đạt tiêu chí?
                if best.fitness > minFitness:
                    break

                difference = abs(best.fitness - lastBestFit)
                if difference <= 0.0000001:
                    bestNotEnhance += 1
                else:
                    lastBestFit = best.fitness
                    bestNotEnhance = 0

                if bestNotEnhance > (maxRepeat / 50):
                    self.reform()

            # lai ghép (crossover)
            offspring = self.crossing(pop[cur])

            # đột biến (mutation)
            self.mutation(offspring)

            pop[cur].extend(offspring)

            # thay thế (replacement)
            pop[next] = self.replacement(pop[cur])
            self._best = pop[next][0] if pop[next][0].dominates(pop[cur][0]) else pop[cur][0]

            self.dualCtrlStrategy(pop[next], bestNotEnhance, nMax)

            cur, next = next, cur
            Trace.trace(self, currentGeneration + 1, bestNotEnhance)
            currentGeneration += 1

    def __str__(self):
        return "NSGA-III với quần thể thích ứng và chiến lược điều khiển kép (APNsgaIII)"
