from setuptools import setup, find_packages

setup(
    name="git-visualizer",
    version="1.2.0",
    description="Simple Git repository visualizer for students",
    author="Git Visualizer Team",
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        "GitPython==3.1.40",
        "Pillow==10.1.0",
        "tkinterdnd2==0.3.0"
    ],
    entry_points={
        'console_scripts': [
            'git-visualizer=main:main',
        ],
    },
    python_requires='>=3.8',
)
