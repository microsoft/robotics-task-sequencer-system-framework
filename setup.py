from setuptools import setup, find_packages

setup(
   name='tasqsym',
   version='1.0',
   description='Robotics Task Sequencer System Framework core and samples',
   author='Microsoft Corporation',
   author_email='robotics@microsoft.com',
   package_dir={'': 'src'},
   packages=find_packages(where='src')
)