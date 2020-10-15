# import pytest

# @pytest.fixture
# def input_value():
#    input = 39
#    return input

# def test_divisible_by_3(input_value):
#    assert input_value % 3 == 0

# def test_divisible_by_6(input_value):
#    assert input_value % 6 == 0
from pytest import fixture
from .model import Project

@fixture
def project() -> Project:
    return Project(
        id=1, project_name='name test', description='it is a test',
    )


def test_Project_create(project: Project):
    assert project


