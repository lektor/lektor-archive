from setuptools import setup

setup(
    name='lektor-demo',
    version='0.1',
    py_modules=['lektor_demo'],
    entry_points={
        'lektor.plugins': [
            'demo = lektor_demo:DemoPlugin',
        ]
    },
    install_requires=[
        'redis'
    ]
)
