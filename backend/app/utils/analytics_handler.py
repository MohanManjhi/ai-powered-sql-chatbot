import pandas as pd
import json
import csv
import tempfile
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class AnalyticsHandler:
    """Handles analytics operations including chart generation and data export"""
    
    def __init__(self):
        self.supported_chart_types = [
            'bar', 'line', 'pie', 'scatter', 'area', 'doughnut', 'horizontal_bar'
        ]
        self.export_formats = ['csv', 'excel', 'json']
    
    def detect_optimal_chart_type(self, rows: List[Dict], question: str) -> str:
        """Automatically detect the best chart type based on data and question"""
        if not rows:
            return "bar"
        
        # Analyze data structure
        num_columns = len(rows[0]) if rows else 0
        num_rows = len(rows)
        
        # Check for time series data
        question_lower = question.lower()
        if any(word in question_lower for word in ['trend', 'over time', 'daily', 'monthly', 'yearly', 'date']):
            return "line"
        
        # Check for comparison data
        if any(word in question_lower for word in ['compare', 'vs', 'versus', 'difference', 'ranking']):
            if num_rows <= 10:
                return "bar"
            else:
                return "horizontal_bar"
        
        # Check for distribution data
        if any(word in question_lower for word in ['distribution', 'frequency', 'count', 'how many']):
            if num_rows <= 20:
                return "bar"
            else:
                return "histogram"
        
        # Check for relationship data
        if any(word in question_lower for word in ['correlation', 'relationship', 'scatter']):
            if num_columns >= 2:
                return "scatter"
        
        # Check for composition data
        if any(word in question_lower for word in ['percentage', 'proportion', 'share', 'breakdown']):
            if num_rows <= 8:
                return "pie"
            else:
                return "doughnut"
        
        # Default based on data characteristics
        if num_rows <= 15:
            return "bar"
        elif num_columns >= 3:
            return "scatter"
        else:
            return "line"
    
    def generate_chart_data(self, rows: List[Dict], chart_type: str, question: str) -> Dict[str, Any]:
        """Generate chart data based on chart type and data"""
        if not rows:
            return {"error": "No data available"}
        
        # Extract column names
        columns = list(rows[0].keys()) if rows else []
        
        if chart_type == "bar":
            return self._generate_bar_chart_data(rows, columns, question)
        elif chart_type == "line":
            return self._generate_line_chart_data(rows, columns, question)
        elif chart_type == "pie":
            return self._generate_pie_chart_data(rows, columns, question)
        elif chart_type == "scatter":
            return self._generate_scatter_chart_data(rows, columns, question)
        elif chart_type == "area":
            return self._generate_area_chart_data(rows, columns, question)
        elif chart_type == "doughnut":
            return self._generate_doughnut_chart_data(rows, columns, question)
        elif chart_type == "horizontal_bar":
            return self._generate_horizontal_bar_chart_data(rows, columns, question)
        else:
            return self._generate_bar_chart_data(rows, columns, question)  # Default fallback
    
    def _generate_bar_chart_data(self, rows: List[Dict], columns: List[str], question: str) -> Dict[str, Any]:
        """Generate bar chart data"""
        if len(columns) < 2:
            return {"error": "Need at least 2 columns for bar chart"}
        
        # Use first column as labels, second as values
        labels = [str(row[columns[0]]) for row in rows[:20]]  # Limit to 20 bars
        values = [float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else 1 for row in rows[:20]]
        
        return {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": columns[1],
                    "data": values,
                    "backgroundColor": self._generate_colors(len(values)),
                    "borderColor": self._generate_colors(len(values)),
                    "borderWidth": 1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Bar Chart: {question[:50]}..."
                    }
                }
            }
        }
    
    def _generate_line_chart_data(self, rows: List[Dict], columns: List[str], question: str) -> Dict[str, Any]:
        """Generate line chart data"""
        if len(columns) < 2:
            return {"error": "Need at least 2 columns for line chart"}
        
        # Sort by first column if it looks like dates
        sorted_rows = sorted(rows, key=lambda x: str(x[columns[0]]))
        
        labels = [str(row[columns[0]]) for row in sorted_rows[:50]]  # Limit to 50 points
        values = [float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else 1 for row in sorted_rows[:50]]
        
        return {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": columns[1],
                    "data": values,
                    "borderColor": "rgb(75, 192, 192)",
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "tension": 0.1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Line Chart: {question[:50]}..."
                    }
                }
            }
        }
    
    def _generate_pie_chart_data(self, rows: List[Dict], columns: List[str], question: str) -> Dict[str, Any]:
        """Generate pie chart data"""
        if len(columns) < 2:
            return {"error": "Need at least 2 columns for pie chart"}
        
        # Group by first column and sum second column
        grouped_data = {}
        for row in rows:
            key = str(row[columns[0]])
            value = float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else 1
            grouped_data[key] = grouped_data.get(key, 0) + value
        
        # Limit to top 8 categories
        sorted_items = sorted(grouped_data.items(), key=lambda x: x[1], reverse=True)[:8]
        labels = [item[0] for item in sorted_items]
        values = [item[1] for item in sorted_items]
        
        return {
            "type": "pie",
            "data": {
                "labels": labels,
                "datasets": [{
                    "data": values,
                    "backgroundColor": self._generate_colors(len(values)),
                    "borderColor": "#fff",
                    "borderWidth": 2
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Pie Chart: {question[:50]}..."
                    }
                }
            }
        }
    
    def _generate_scatter_chart_data(self, rows: List[Dict], columns: List[str], question: str) -> Dict[str, Any]:
        """Generate scatter chart data"""
        if len(columns) < 3:
            return {"error": "Need at least 3 columns for scatter chart"}
        
        # Use first two columns as x,y coordinates
        x_values = [float(row[columns[0]]) if isinstance(row[columns[0]], (int, float)) else i for i, row in enumerate(rows[:100])]
        y_values = [float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else i for i, row in enumerate(rows[:100])]
        
        return {
            "type": "scatter",
            "data": {
                "datasets": [{
                    "label": f"{columns[0]} vs {columns[1]}",
                    "data": [{"x": x, "y": y} for x, y in zip(x_values, y_values)],
                    "backgroundColor": "rgba(75, 192, 192, 0.6)",
                    "borderColor": "rgb(75, 192, 192)"
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Scatter Plot: {question[:50]}..."
                    }
                },
                "scales": {
                    "x": {"title": {"display": True, "text": columns[0]}},
                    "y": {"title": {"display": True, "text": columns[1]}}
                }
            }
        }
    
    def _generate_area_chart_data(self, rows: List[Dict], columns: List[str], question: str) -> Dict[str, Any]:
        """Generate area chart data"""
        if len(columns) < 2:
            return {"error": "Need at least 2 columns for area chart"}
        
        sorted_rows = sorted(rows, key=lambda x: str(x[columns[0]]))
        labels = [str(row[columns[0]]) for row in sorted_rows[:50]]
        values = [float(row[columns[1]]) if isinstance(row[columns[1]], (int, float)) else 1 for row in sorted_rows[:50]]
        
        return {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": columns[1],
                    "data": values,
                    "backgroundColor": "rgba(75, 192, 192, 0.3)",
                    "borderColor": "rgb(75, 192, 192)",
                    "fill": True,
                    "tension": 0.1
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Area Chart: {question[:50]}..."
                    }
                }
            }
        }
    
    def _generate_doughnut_chart_data(self, rows: List[Dict], columns: List[str], question: str) -> Dict[str, Any]:
        """Generate doughnut chart data"""
        pie_data = self._generate_pie_chart_data(rows, columns, question)
        if "error" in pie_data:
            return pie_data
        
        pie_data["type"] = "doughnut"
        return pie_data
    
    def _generate_horizontal_bar_chart_data(self, rows: List[Dict], columns: List[str], question: str) -> Dict[str, Any]:
        """Generate horizontal bar chart data"""
        bar_data = self._generate_bar_chart_data(rows, columns, question)
        if "error" in bar_data:
            return bar_data
        
        bar_data["type"] = "horizontalBar"
        return bar_data
    
    def _generate_colors(self, count: int) -> List[str]:
        """Generate a list of colors for charts"""
        colors = [
            "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
            "#FF9F40", "#FF6384", "#C9CBCF", "#4BC0C0", "#FF6384"
        ]
        
        if count <= len(colors):
            return colors[:count]
        
        # Generate additional colors if needed
        import random
        additional_colors = []
        for _ in range(count - len(colors)):
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            additional_colors.append(f"rgb({r}, {g}, {b})")
        
        return colors + additional_colors
    
    def get_chart_suggestions(self, chart_type: str, rows: List[Dict]) -> List[str]:
        """Get suggestions for the current chart"""
        suggestions = []
        
        if chart_type == "bar":
            suggestions.extend([
                "Try asking for trends over time to see line charts",
                "Ask for percentages to see pie charts",
                "Request comparisons between categories"
            ])
        elif chart_type == "line":
            suggestions.extend([
                "Ask for category breakdowns to see bar charts",
                "Request distribution analysis for histograms",
                "Ask for correlations between variables"
            ])
        elif chart_type == "pie":
            suggestions.extend([
                "Ask for trends over time to see line charts",
                "Request detailed breakdowns with bar charts",
                "Ask for comparisons between specific categories"
            ])
        
        suggestions.extend([
            "Download this data for further analysis",
            "Try different chart types for better visualization",
            "Ask for specific insights about the data"
        ])
        
        return suggestions
    
    def generate_export_file(self, rows: List[Dict], export_format: str, filename: str) -> Dict[str, Any]:
        """Generate export file in specified format"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = safe_filename.replace(' ', '_')
        
        if export_format == "csv":
            return self._generate_csv_export(rows, safe_filename, timestamp)
        elif export_format == "excel":
            return self._generate_excel_export(rows, safe_filename, timestamp)
        elif export_format == "json":
            return self._generate_json_export(rows, safe_filename, timestamp)
        else:
            return self._generate_csv_export(rows, safe_filename, timestamp)  # Default to CSV
    
    def _generate_csv_export(self, rows: List[Dict], filename: str, timestamp: str) -> Dict[str, Any]:
        """Generate CSV export"""
        if not rows:
            return {"error": "No data to export"}
        
        # Create downloads directory if it doesn't exist
        downloads_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Create file in downloads directory
        file_path = os.path.join(downloads_dir, f"{filename}_{timestamp}.csv")
        
        # Write CSV data
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        return {
            "download_url": f"/downloads/{filename}_{timestamp}.csv",
            "filename": f"{filename}_{timestamp}.csv",
            "file_path": file_path
        }
    
    def _generate_excel_export(self, rows: List[Dict], filename: str, timestamp: str) -> Dict[str, Any]:
        """Generate Excel export"""
        try:
            df = pd.DataFrame(rows)
            
            # Create downloads directory if it doesn't exist
            downloads_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'downloads')
            os.makedirs(downloads_dir, exist_ok=True)
            
            # Create file in downloads directory
            file_path = os.path.join(downloads_dir, f"{filename}_{timestamp}.xlsx")
            
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
            
            return {
                "download_url": f"/downloads/{filename}_{timestamp}.xlsx",
                "filename": f"{filename}_{timestamp}.xlsx",
                "file_path": file_path
            }
        except ImportError:
            # Fallback to CSV if pandas/openpyxl not available
            return self._generate_csv_export(rows, filename, timestamp)
    
    def _generate_json_export(self, rows: List[Dict], filename: str, timestamp: str) -> Dict[str, Any]:
        """Generate JSON export"""
        # Create downloads directory if it doesn't exist
        downloads_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Create file in downloads directory
        file_path = os.path.join(downloads_dir, f"{filename}_{timestamp}.json")
        
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(rows, jsonfile, indent=2, default=str)
        
        return {
            "download_url": f"/downloads/{filename}_{timestamp}.json",
            "filename": f"{filename}_{timestamp}.json",
            "file_path": file_path
        }
    
    def generate_analytics_suggestions(self, schema: Dict[str, Any]) -> List[str]:
        """Generate analytics suggestions based on database schema"""
        suggestions = []
        
        for table_name, columns in schema.items():
            # Sales/Revenue analysis
            if any(word in table_name.lower() for word in ['sale', 'order', 'transaction', 'revenue']):
                suggestions.extend([
                    f"Show sales trends over time from {table_name}",
                    f"Compare sales by category in {table_name}",
                    f"Calculate total revenue from {table_name}",
                    f"Show top performing products in {table_name}"
                ])
            
            # User/Customer analysis
            if any(word in table_name.lower() for word in ['user', 'customer', 'client']):
                suggestions.extend([
                    f"Show user growth over time from {table_name}",
                    f"Analyze customer demographics in {table_name}",
                    f"Show customer retention rates from {table_name}",
                    f"Compare user activity patterns in {table_name}"
                ])
            
            # Product/Inventory analysis
            if any(word in table_name.lower() for word in ['product', 'inventory', 'item']):
                suggestions.extend([
                    f"Show inventory levels in {table_name}",
                    f"Analyze product performance in {table_name}",
                    f"Show stock turnover rates in {table_name}",
                    f"Compare product categories in {table_name}"
                ])
        
        return suggestions[:10]  # Limit to 10 suggestions
    
    def get_available_chart_types(self) -> List[Dict[str, Any]]:
        """Get list of available chart types with descriptions"""
        return [
            {
                "type": "bar",
                "name": "Bar Chart",
                "description": "Best for comparing categories or showing rankings",
                "best_for": ["Comparisons", "Rankings", "Categorical data"]
            },
            {
                "type": "line",
                "name": "Line Chart",
                "description": "Best for showing trends over time",
                "best_for": ["Time series", "Trends", "Continuous data"]
            },
            {
                "type": "pie",
                "name": "Pie Chart",
                "description": "Best for showing parts of a whole",
                "best_for": ["Percentages", "Proportions", "Composition"]
            },
            {
                "type": "scatter",
                "name": "Scatter Plot",
                "description": "Best for showing relationships between variables",
                "best_for": ["Correlations", "Relationships", "Two variables"]
            },
            {
                "type": "area",
                "name": "Area Chart",
                "description": "Best for showing cumulative data over time",
                "best_for": ["Cumulative data", "Time series", "Volume"]
            },
            {
                "type": "doughnut",
                "name": "Doughnut Chart",
                "description": "Alternative to pie charts with better readability",
                "best_for": ["Percentages", "Proportions", "Modern look"]
            },
            {
                "type": "horizontal_bar",
                "name": "Horizontal Bar Chart",
                "description": "Better for long category names",
                "best_for": ["Long labels", "Many categories", "Readability"]
            }
        ]

# Create a global instance
analytics_handler = AnalyticsHandler()
