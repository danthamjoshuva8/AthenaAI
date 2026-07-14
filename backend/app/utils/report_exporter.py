import csv
import os


class ReportExporter:

    def export_csv(
        self,
        results,
        filename="optimization_report.csv"
    ):

        folder = "reports"

        os.makedirs(folder, exist_ok=True)

        filepath = os.path.join(folder, filename)

        if len(results) == 0:
            return filepath

        with open(
            filepath,
            "w",
            newline=""
        ) as csvfile:

            writer = csv.DictWriter(

                csvfile,

                fieldnames=results[0].keys()

            )

            writer.writeheader()

            writer.writerows(results)

        return filepath