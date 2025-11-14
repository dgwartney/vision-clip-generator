"""Entry point for running vision-clip-generator as a module.

This allows the application to be run using:
    python -m vision_clip_generator --file dialogs/test.txt --record 1

The module name uses underscores (vision_clip_generator) following Python
module naming conventions, while the package name uses hyphens.
"""

from main import main

if __name__ == '__main__':
    exit(main())
