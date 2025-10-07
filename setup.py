from setuptools import setup, find_packages

setup(
    name="git-visualizer",
    version="1.3.0",
    description="Simple Git repository visualizer for students",
    author="Git Visualizer Team",
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        "GitPython==3.1.45",
        "Pillow==11.0.0",
        "tkinterdnd2==0.4.2",
        "requests==2.32.3"
    ],
    entry_points={
        'console_scripts': [
            'git-visualizer=main:main',
        ],
    },
    python_requires='>=3.8',
)
