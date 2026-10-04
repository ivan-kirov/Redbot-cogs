import setuptools

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="redbot-cog-wowroster",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="World of Warcraft Roster Management for Redbot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/Redbot-cogs",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "redbot-core>=4.0.0",
        "google-api-python-client>=2.0.0",
        "google-auth-httplib2>=0.1.0",
        "pytest>=7.0.0",
    ],
    entry_points={
        "redbot.cogs": [
            "wowroster = wowroster.wowroster:setup",
        ],
    },
)
