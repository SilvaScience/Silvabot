# Silvabot
Modules and code related to Silvabot
# Documentation
Stills needs to be implemented

Follow common [Python DocStrings guidelines](https://www.doxygen.nl/manual/docblocks.html#pythonblocks)

# Contributing
## Setting up your Python environnement
1. Install [miniconda](https://docs.anaconda.com/free/miniconda/miniconda-install/) or [Anaconda](https://docs.anaconda.com/free/anaconda/install/) environnement managers
2. Create a virtual environnement for the Colberto project using `conda create -n colberto_mybranch` or the Anaconda GUI interface and active it `conda activate colberto_mybranch`
3. Navigate to the dependencies folder and update the virtual environnement using `conda install --yes --file requirements.txt`. Conda will install the packages required for the current branch. You might need to run `conda config --add channels conda-forge` and `conda config --set channel_priority strict` to add a channel where some pacakge are available.

4. You can then locate your environnement using which `which python` in Linux or `where python` in Windows and import it into your IDE (e.g. VCode with Python pluggin)
## Updating python environnement

When developping new features in your branch, it is very likely that you will need to add python packages. You can do this using `conda install packagename`. You will then need to update the required package list by naviguating to /dependencies/ and using the command `conda list -e > requirements.txt`. This will dump your current package list into the file so that the packages will be appended to the project requirements. Don't forget to add requirements.txt to your commit.

## Naming Conventions
In this project, we follow standard Python naming conventions to ensure that our code is readable and consistent. Below are the guidelines for naming functions and classes:
## Folder structure

- `/dependencies` : Put conda dependencies list here
- `/src` : This is where the code goes and is further divided into subcategories
-- `/src/drivers` : Let's put all the driver modules in here e.g. SLM.py or Streising.py etc...
-- `/src/gui`: Code related to the graphical user interface
-- `/src/compute`: Code that perform internal various computations such as fitting, computing quantitie etc...
-- `/src/io` : Code related to loading and saving various types of data or calibrations
- `/samples` : Code showing how to use the different modules using `import modulename.` Keep same subdirectory structure as /src

### Classes
Classes are named using the CamelCase convention. This means that each word within the class name starts with a capital letter and there are no underscores between words. This helps in distinguishing class names from function and variable names.

Examples:
ImageGenerator
EmployeeRecord

### Functions and Methods
Functions and methods are named using the snake_case convention. This means that all letters are in lowercase and words are separated by underscores. This makes function and method names easy to read and understand.

Examples:
get_depth()
write_image()
send_email()
