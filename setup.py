import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bag2video",
    version="0.0.1",
    author="Aaron Marburg",
    author_email="amarburg@uw.edu",
    description="Scripts to process ROS bagfiles into videos",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/apl-ocean-engineering/bag2video",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    scripts=['bag2video.py', 'bag2images.py'],
    install_requires=['numpy', 'opencv-python', 'imageio', 'rosbags', 'rosbags-image'],
    entry_points={
    'console_scripts': [
        'bag2video=bag2video:main', 
        'bag2images=bag2images:main'
    ],
    }
)
