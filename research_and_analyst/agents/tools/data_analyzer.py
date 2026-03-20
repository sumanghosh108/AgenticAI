"""
Data Analyzer Tool — executes Python analysis code in a sandboxed environment.
Provides pandas-based data analysis and statistical computations.
"""

import io
import sys
import traceback
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from research_and_analyst.logger import GLOBAL_LOGGER as log


class AnalysisResult(BaseModel):
    success: bool = True
    output: str = ""
    error: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)


class DataAnalyzerTool:
    """Executes data analysis using pandas within a restricted namespace."""

    ALLOWED_MODULES = {"pandas", "numpy", "statistics", "math", "json", "collections"}

    def analyze(self, code: str, input_data: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Execute analysis code with optional input data injected as variables.

        Args:
            code: Python code string to execute (must be pandas/numpy safe).
            input_data: Dict of variable names → values to inject into the namespace.
        """
        try:
            import pandas as pd
            import numpy as np
            import json
            import statistics
            import math
            from collections import Counter, defaultdict

            namespace = {
                "pd": pd,
                "np": np,
                "json": json,
                "statistics": statistics,
                "math": math,
                "Counter": Counter,
                "defaultdict": defaultdict,
                "result": {},
            }

            if input_data:
                namespace.update(input_data)

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            try:
                exec(code, namespace)  # noqa: S102
            finally:
                sys.stdout = old_stdout

            output = buffer.getvalue()
            result_data = namespace.get("result", {})

            log.info("Analysis executed successfully", output_lines=output.count("\n") + 1)
            return AnalysisResult(output=output, data=result_data)

        except Exception as e:
            error_msg = traceback.format_exc()
            log.error("Analysis execution failed", error=str(e))
            return AnalysisResult(success=False, error=error_msg)

    def analyze_csv(self, csv_content: str, analysis_prompt: str) -> AnalysisResult:
        """Quick analysis of CSV data: load + describe."""
        code = f"""
import pandas as pd
import io

df = pd.read_csv(io.StringIO(csv_data))
print("Shape:", df.shape)
print("\\nColumns:", list(df.columns))
print("\\nData Types:\\n", df.dtypes.to_string())
print("\\nDescriptive Statistics:\\n", df.describe().to_string())
print("\\nMissing Values:\\n", df.isnull().sum().to_string())
result = {{
    "shape": list(df.shape),
    "columns": list(df.columns),
    "summary": df.describe().to_dict(),
}}
"""
        return self.analyze(code, {"csv_data": csv_content})

    def compute_kpis(self, data: Dict[str, Any], kpi_definitions: List[str]) -> AnalysisResult:
        """Compute KPIs from structured data given a list of KPI definitions."""
        kpi_code = """
result = {}
for kpi_name in kpi_list:
    kpi_lower = kpi_name.lower()
    if kpi_lower in data:
        result[kpi_name] = data[kpi_lower]
    else:
        result[kpi_name] = "Not available in provided data"
print(json.dumps(result, indent=2, default=str))
"""
        return self.analyze(kpi_code, {"data": data, "kpi_list": kpi_definitions})
