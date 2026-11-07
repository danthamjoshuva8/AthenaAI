import math


class ObjectUtils:
    """
    Provides utility methods for inspecting and cleaning nested objects.

    Supports dictionaries and lists containing nested values.
    Identifies non-finite floating-point values such as NaN and Infinity
    and replaces them with None when cleaning an object.
    """

    def find_bad(self, obj, path="root"):
        """
        Recursively identify NaN and Infinity values in an object.

        Traverses nested dictionaries and lists while maintaining
        the object's location path for each detected non-finite value.

        Args:
            obj: Object to inspect, including nested dictionaries and lists.
            path: Current location within the object. Defaults to "root".

        Returns:
            None. Prints the paths of detected NaN and Infinity values.
        """

        # Inspect each key-value pair in a dictionary.
        if isinstance(obj, dict):
            for k, v in obj.items():

                # Recursively inspect the value and extend its location path.
                self.find_bad(v, f"{path}.{k}")

        # Inspect each element in a list.
        elif isinstance(obj, list):
            for i, v in enumerate(obj):

                # Recursively inspect the element using its list index.
                self.find_bad(v, f"{path}[{i}]")

        # Check floating-point values for non-finite numbers.
        elif isinstance(obj, float):
            if math.isnan(obj):
                print("NaN:", path)

            elif math.isinf(obj):
                print("Infinity:", path)

    def clean(self, obj):
        """
        Recursively clean an object by replacing NaN and Infinity values.

        Traverses nested dictionaries and lists while preserving their
        structure. Non-finite floating-point values are replaced with None.

        Args:
            obj: Object to clean, including nested dictionaries and lists.

        Returns:
            A cleaned object with the original structure preserved and
            NaN or Infinity floating-point values replaced with None.
        """

        # Recursively clean every value in a dictionary.
        if isinstance(obj, dict):
            return {k: self.clean(v) for k, v in obj.items()}

        # Recursively clean every element in a list.
        if isinstance(obj, list):
            return [self.clean(v) for v in obj]

        # Replace NaN and positive or negative Infinity with None.
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None

        # Preserve all other values without modification.
        return obj