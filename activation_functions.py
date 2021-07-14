from math import sin, cos, tan, exp, pi, sqrt


# abs
def fun_abs(number):
    return abs(number)


# sin
def fun_sin(number):
    return sin(number)


def fun_sin_4x(number):
    return sin(number * 4)


def fun_sin_10x(number):
    return sin(number * 10)


# cos
def fun_cos(number):
    return cos(number)


def fun_cos_4x(number):
    return cos(number * 4)


def fun_cos_10x(number):
    return cos(number * 10)


# tan
def fun_tan(number):
    return tan(number)


def fun_tan_4x(number):
    return tan(number * 4)


def fun_tan_10x(number):
    return tan(number * 10)


# ramp
def fun_ramp(number):
    return number


# gauss
def fun_gauss(number):
    sigma = 0.4
    power = (number/sigma) ** 2
    power *= (-1/2)
    exponential = exp(power)
    denominator = sqrt(2 * pi)
    denominator *= sigma

    return exponential / denominator


# step
def fun_step(number):
    if number < 0:
        return -1
    else:
        return 1


# sigmoid
def fun_sigmoid(number):
    if number > 10:
        ans = 1
    elif number < -10:
        ans = 0
    else:
        ans = 1 / (1 + exp(-number))

    return ans


# square root of absolute value
def fun_abs_sqrt(number):
    return sqrt(abs(number))


# square
def fun_square(number):
    return number ** 2


# Sawtooth
def fun_sawtooth(number):
    return number - int(number)
