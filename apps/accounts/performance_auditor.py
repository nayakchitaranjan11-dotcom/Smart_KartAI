"""
THE PERFORMANCE AUDITOR  (standalone Data-Structures / complexity assignment script)
==================================================================================
This file is NOT imported by the Django web app - it is a separate Python program
that benchmarks O(1), O(log n), O(n), O(n log n) and O(n^2) algorithms and plots
their growth with matplotlib.

Run it on its own from the project folder:
    pip install matplotlib
    python apps/accounts/performance_auditor.py

(Repaired: the original copy had lost the indentation of every function/loop body
 and contained Markdown ``` fences, so Python could not even parse it.)
"""

# ============================================================

# THE PERFORMANCE AUDITOR

# Foundations & Complexity Analysis of Data Structures

# ============================================================

import timeit
import tracemalloc
import math
import sys
import gc
import matplotlib.pyplot as plt

# ============================================================

# 1. CLASSIFICATION OF DATA STRUCTURES

# ============================================================

print("\n" + "=" * 60)
print("1. CLASSIFICATION OF DATA STRUCTURES")
print("=" * 60)

# Primitive Data Structures

integer_value = 100
float_value = 25.5
character_value = "A"
boolean_value = True

# Non-Primitive Linear Data Structures

array_ds = [10, 20, 30, 40, 50]
stack_ds = []
queue_ds = []

# Non-Primitive Non-Linear Data Structures

tree_ds = {
"root": {
"left": 10,
"right": 20
}
}

graph_ds = {
"A": ["B", "C"],
"B": ["A", "D"],
"C": ["A", "D"],
"D": ["B", "C"]
}

print("\nPrimitive Data Structures:")
print("Integer:", integer_value)
print("Float:", float_value)
print("Character:", character_value)
print("Boolean:", boolean_value)

print("\nLinear Data Structures:")
print("Array/List:", array_ds)

print("\nNon-Linear Data Structures:")
print("Tree:", tree_ds)
print("Graph:", graph_ds)

# ============================================================

# 2. MEMORY MAPPING

# ============================================================

print("\n" + "=" * 60)
print("2. MEMORY MAPPING")
print("=" * 60)

def memory_mapping_demo():

    # Different Python objects
    number = 100
    numbers = [1, 2, 3, 4, 5]

    print("\nMemory Address of Integer:")
    print(id(number))

    print("\nMemory Address of List:")
    print(id(numbers))

    print("\nSize of Integer:")
    print(sys.getsizeof(number), "bytes")

    print("\nSize of List:")
    print(sys.getsizeof(numbers), "bytes")

    print("\nMemory Address of Each List Element:")

    for index, value in enumerate(numbers):
        print(
            "Index:",
            index,
            "| Value:",
            value,
            "| Memory Address:",
            id(value)
        )

memory_mapping_demo()

# ============================================================

# 3. ASYMPTOTIC NOTATIONS

# ============================================================

print("\n" + "=" * 60)
print("3. ASYMPTOTIC NOTATIONS")
print("=" * 60)

print("""
Big-O (O):
Represents the upper bound / worst-case complexity.

Omega (Ω):
Represents the lower bound / best-case complexity.

Theta (Θ):
Represents the tight bound when upper and lower bounds
grow at the same rate.
""")

# ============================================================

# ALGORITHM 1: CONSTANT TIME - O(1)

# ============================================================

def constant_algorithm(data):

    if len(data) > 0:
        return data[0]

    return None

# ============================================================

# ALGORITHM 2: LOGARITHMIC TIME - O(log n)

# Binary Search

# ============================================================

def logarithmic_algorithm(data, target):

    left = 0
    right = len(data) - 1

    while left <= right:

        middle = (left + right) // 2

        if data[middle] == target:
            return middle

        elif data[middle] < target:
            left = middle + 1

        else:
            right = middle - 1

    return -1

# ============================================================

# ALGORITHM 3: LINEAR TIME - O(n)

# ============================================================

def linear_algorithm(data):

    total = 0

    for value in data:
        total += value

    return total

# ============================================================

# ALGORITHM 4: LINEARITHMIC TIME - O(n log n)

# Python built-in sorting

# ============================================================

def linearithmic_algorithm(data):

    return sorted(data)

# ============================================================

# ALGORITHM 5: QUADRATIC TIME - O(n²)

# Bubble Sort

# ============================================================

def quadratic_algorithm(data):

    data = data.copy()

    n = len(data)

    for i in range(n):

        for j in range(0, n - i - 1):

            if data[j] > data[j + 1]:

                data[j], data[j + 1] = \
                    data[j + 1], data[j]

    return data

# ============================================================

# 4. DYNAMIC MEMORY MANAGEMENT

# ============================================================

print("\n" + "=" * 60)
print("4. DYNAMIC MEMORY MANAGEMENT")
print("=" * 60)

def dynamic_memory_demo():

    print("\nCreating a dynamically growing list...")

    dynamic_list = []

    for i in range(10):

        dynamic_list.append(i)

        print(
            "Elements:",
            len(dynamic_list),
            "| Memory Size:",
            sys.getsizeof(dynamic_list),
            "bytes"
        )

    print("\nDeleting dynamic memory reference...")

    del dynamic_list

    # Request garbage collection
    gc.collect()

    print("Garbage collection completed.")

dynamic_memory_demo()

# ============================================================

# 5. TIME-SPACE TRADE-OFF ANALYSIS

# ============================================================

print("\n" + "=" * 60)
print("5. TIME-SPACE TRADE-OFF ANALYSIS")
print("=" * 60)

# ------------------------------------------------------------

# METHOD 1:

# Uses less memory but takes more time

# Linear Search

# ------------------------------------------------------------

def linear_search(data, target):

    for i in range(len(data)):

        if data[i] == target:
            return i

    return -1

# ------------------------------------------------------------

# METHOD 2:

# Uses more memory but provides faster lookup

# Dictionary / Hash Table

# ------------------------------------------------------------

def dictionary_lookup(data, target):

    lookup_table = {}

    for index, value in enumerate(data):

        lookup_table[value] = index

    return lookup_table.get(target, -1)

def compare_time_space_tradeoff():

    print("\nComparing Linear Search and Dictionary Lookup")

    sizes = [100, 1000, 5000, 10000]

    for size in sizes:

        data = list(range(size))
        target = size - 1

        # ----------------------------
        # Linear Search Memory
        # ----------------------------

        tracemalloc.start()

        start_time = timeit.default_timer()

        linear_search(data, target)

        end_time = timeit.default_timer()

        current, peak = tracemalloc.get_traced_memory()

        tracemalloc.stop()

        linear_time = end_time - start_time
        linear_memory = peak

        # ----------------------------
        # Dictionary Lookup Memory
        # ----------------------------

        tracemalloc.start()

        start_time = timeit.default_timer()

        dictionary_lookup(data, target)

        end_time = timeit.default_timer()

        current, peak = tracemalloc.get_traced_memory()

        tracemalloc.stop()

        dictionary_time = end_time - start_time
        dictionary_memory = peak

        print("\nInput Size:", size)

        print(
            "Linear Search ->",
            "Time:",
            linear_time,
            "Memory:",
            linear_memory,
            "bytes"
        )

        print(
            "Dictionary Lookup ->",
            "Time:",
            dictionary_time,
            "Memory:",
            dictionary_memory,
            "bytes"
        )

compare_time_space_tradeoff()

# ============================================================

# 6. PERFORMANCE AUDITOR

# ============================================================

print("\n" + "=" * 60)
print("6. THE PERFORMANCE AUDITOR")
print("=" * 60)

# Input sizes

input_sizes = [
10,
50,
100,
200,
500,
1000
]

constant_times = []
logarithmic_times = []
linear_times = []
linearithmic_times = []
quadratic_times = []

# ============================================================

# BENCHMARK FUNCTION

# ============================================================

def benchmark(function, *args, repetitions=5):

    timer = timeit.Timer(
        lambda: function(*args)
    )

    execution_time = timer.timeit(
        number=repetitions
    )

    average_time = execution_time / repetitions

    return average_time

# ============================================================

# RUN PERFORMANCE TESTS

# ============================================================

for size in input_sizes:

    print("\nTesting Input Size:", size)

    # Create input data
    data = list(range(size, 0, -1))

    sorted_data = sorted(data)

    # Constant O(1)
    constant_time = benchmark(
        constant_algorithm,
        data
    )

    constant_times.append(
        constant_time
    )

    # Logarithmic O(log n)
    logarithmic_time = benchmark(
        logarithmic_algorithm,
        sorted_data,
        sorted_data[-1]
    )

    logarithmic_times.append(
        logarithmic_time
    )

    # Linear O(n)
    linear_time = benchmark(
        linear_algorithm,
        data
    )

    linear_times.append(
        linear_time
    )

    # Linearithmic O(n log n)
    linearithmic_time = benchmark(
        linearithmic_algorithm,
        data
    )

    linearithmic_times.append(
        linearithmic_time
    )

    # Quadratic O(n²)
    #
    # Avoid extremely large sizes because
    # Bubble Sort becomes very slow.

    if size <= 1000:

        quadratic_time = benchmark(
            quadratic_algorithm,
            data,
            repetitions=1
        )

        quadratic_times.append(
            quadratic_time
        )

    else:

        quadratic_times.append(
            None
        )

# ============================================================

# 7. DISPLAY PERFORMANCE RESULTS

# ============================================================

print("\n" + "=" * 60)
print("PERFORMANCE RESULTS")
print("=" * 60)

print(
"\nSize\tO(1)\t\tO(log n)\tO(n)\t\tO(n log n)\tO(n²)"
)

for i in range(len(input_sizes)):

    print(
        input_sizes[i],
        "\t",
        f"{constant_times[i]:.8f}",
        "\t",
        f"{logarithmic_times[i]:.8f}",
        "\t",
        f"{linear_times[i]:.8f}",
        "\t",
        f"{linearithmic_times[i]:.8f}",
        "\t",
        f"{quadratic_times[i]:.8f}"
    )

# ============================================================

# 8. MEMORY PERFORMANCE AUDITOR

# ============================================================

print("\n" + "=" * 60)
print("MEMORY PERFORMANCE ANALYSIS")
print("=" * 60)

def memory_benchmark(function, *args):

    tracemalloc.start()

    function(*args)

    current, peak = tracemalloc.get_traced_memory()

    tracemalloc.stop()

    return peak

memory_sizes_linear = []
memory_sizes_sort = []
memory_sizes_quadratic = []

for size in input_sizes:

    data = list(range(size, 0, -1))

    linear_memory = memory_benchmark(
        linear_algorithm,
        data
    )

    memory_sizes_linear.append(
        linear_memory
    )

    sort_memory = memory_benchmark(
        linearithmic_algorithm,
        data
    )

    memory_sizes_sort.append(
        sort_memory
    )

    quadratic_memory = memory_benchmark(
        quadratic_algorithm,
        data
    )

    memory_sizes_quadratic.append(
        quadratic_memory
    )

print("\nSize\tLinear\tSort\tBubble Sort")

for i in range(len(input_sizes)):

    print(
        input_sizes[i],
        "\t",
        memory_sizes_linear[i],
        "\t",
        memory_sizes_sort[i],
        "\t",
        memory_sizes_quadratic[i]
    )

# ============================================================

# 9. PLOT ACTUAL EXECUTION TIMES

# ============================================================

plt.figure()

plt.plot(
input_sizes,
constant_times,
marker="o",
label="O(1)"
)

plt.plot(
input_sizes,
logarithmic_times,
marker="o",
label="O(log n)"
)

plt.plot(
input_sizes,
linear_times,
marker="o",
label="O(n)"
)

plt.plot(
input_sizes,
linearithmic_times,
marker="o",
label="O(n log n)"
)

plt.plot(
input_sizes,
quadratic_times,
marker="o",
label="O(n²)"
)

plt.xlabel("Input Size (n)")

plt.ylabel(
"Average Execution Time (seconds)"
)

plt.title(
"The Performance Auditor: Actual Algorithm Performance"
)

plt.legend()

plt.grid(True)

plt.show()

# ============================================================

# 10. PLOT THEORETICAL GROWTH RATES

# ============================================================

growth_n = list(
range(1, 101)
)

growth_constant = [
1
for n in growth_n
]

growth_log = [
math.log2(n)
for n in growth_n
]

growth_linear = [
n
for n in growth_n
]

growth_nlogn = [
n * math.log2(n)
for n in growth_n
]

growth_quadratic = [
n ** 2
for n in growth_n
]

plt.figure()

plt.plot(
growth_n,
growth_constant,
label="O(1)"
)

plt.plot(
growth_n,
growth_log,
label="O(log n)"
)

plt.plot(
growth_n,
growth_linear,
label="O(n)"
)

plt.plot(
growth_n,
growth_nlogn,
label="O(n log n)"
)

plt.plot(
growth_n,
growth_quadratic,
label="O(n²)"
)

plt.xlabel("Input Size (n)")

plt.ylabel(
"Relative Number of Operations"
)

plt.title(
"Theoretical Growth Rates of Algorithms"
)

plt.legend()

plt.grid(True)

plt.show()

# ============================================================

# 11. PLOT MEMORY USAGE

# ============================================================

plt.figure()

plt.plot(
input_sizes,
memory_sizes_linear,
marker="o",
label="Linear Algorithm"
)

plt.plot(
input_sizes,
memory_sizes_sort,
marker="o",
label="Sorting Algorithm"
)

plt.plot(
input_sizes,
memory_sizes_quadratic,
marker="o",
label="Bubble Sort"
)

plt.xlabel("Input Size")

plt.ylabel(
"Peak Memory Usage (bytes)"
)

plt.title(
"Memory Consumption Analysis"
)

plt.legend()

plt.grid(True)

plt.show()

# ============================================================

# 12. BOTTLENECK IDENTIFICATION

# ============================================================

print("\n" + "=" * 60)
print("BOTTLENECK ANALYSIS")
print("=" * 60)

for i in range(len(input_sizes)):

    size = input_sizes[i]

    max_time = max(
        constant_times[i],
        logarithmic_times[i],
        linear_times[i],
        linearithmic_times[i],
        quadratic_times[i]
    )

    if max_time == quadratic_times[i]:

        bottleneck = "Quadratic Algorithm O(n²)"

    elif max_time == linearithmic_times[i]:

        bottleneck = "Sorting Algorithm O(n log n)"

    elif max_time == linear_times[i]:

        bottleneck = "Linear Algorithm O(n)"

    elif max_time == logarithmic_times[i]:

        bottleneck = "Logarithmic Algorithm O(log n)"

    else:

        bottleneck = "Constant Algorithm O(1)"

    print(
        "\nInput Size:",
        size,
        "| Efficiency Bottleneck:",
        bottleneck
    )

# ============================================================

# 13. COMPLEXITY SUMMARY

# ============================================================

print("\n" + "=" * 60)
print("COMPLEXITY SUMMARY")
print("=" * 60)

print("""
Algorithm              Time Complexity       Space Complexity

Array Access           O(1)                  O(1)

Binary Search          O(log n)              O(1)

Linear Traversal       O(n)                  O(1)

Python Sorting         O(n log n)            O(n)

Bubble Sort            O(n²)                 O(n)

Dictionary Lookup      O(1) average          O(n)

ASYMPTOTIC NOTATION:

Big-O:
Worst-case upper bound.

Omega:
Best-case lower bound.

Theta:
Tight bound representing the exact growth order.

TIME-SPACE TRADE-OFF:

Using additional memory, such as a dictionary/hash table,
can reduce lookup time.

Example:

Linear Search:
Time  = O(n)
Space = O(1)

Hash Table Lookup:
Time  = O(1) average
Space = O(n)

BOTTLENECK:

The O(n²) algorithm generally becomes the major
performance bottleneck as input size increases.
""")

print("\nPerformance Auditor Completed Successfully!")

# ============================================================
