N = int(input("Enter integer N:"))

for i in range(1, N + 1):
    if i % 15 == 0:
        print("FizzBuzz")
    if i % 3 == 0:
        print("Fizz")
    if i % 5 == 0:
        print("Buzz")
    else:
        print(i)