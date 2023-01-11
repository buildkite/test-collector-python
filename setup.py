from setuptools import setup, find_packages
from src.buildkite_test_collector.collector import constants

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name=constants.COLLECTOR_NAME,
      version=constants.VERSION,
      description='Buildkite Test Analytics collector',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/buildkite/test-collector-python',
      author='James Harton',
      author_email='james.harton@alembic.com.au',
      license='MIT',
      classifiers=[
          "License :: OSI Approved :: MIT License",
          "Framework :: Pytest"
      ],
      py_modules=['buildkite_test_collector'],
      zip_safe=False,
      package_dir={'': 'src'},
      packages=find_packages(where='src'),
      install_requires=["requests>=2", "pytest>=7"],
      extras_require={
          "dev": [
              "mock>=4",
              "check-manifest",
              "twine",
              "responses",
              "pylint"
          ]
      },
      entry_points={
          "pytest11": ["buildkite-test-collector = buildkite_test_collector.pytest_plugin"]
      },
      python_requires=">=3.8")
