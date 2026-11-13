"""Static-analysis fixture only. Never import or execute this module."""


def vulnerable_expression(untrusted):
    return eval(untrusted)
