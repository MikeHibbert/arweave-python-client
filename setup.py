import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="arweave-python-client", # Replace with your own username
    version="0.0.1",
    author="Mike Hibbert",
    author_email="mike@hibbertitsolutions.co.uk",
    description="Client interface for sending transactions on the Arweave permaweb",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MikeHibbert/arweave-python-client",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)