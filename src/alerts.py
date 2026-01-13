"""
Alerts Module - CloudWalk Operations Intelligence

This module implements anomaly detection using Z-score statistics.
It monitors key metrics and generates alerts when values deviate
significantly from historical patterns.

Z-Score Formula:
    z = (value - mean) / std

Interpretation:
    Z < -2: Significant drop (warning)
    Z < -3: Critical drop (alert)
    Z > 2: Significant spike (warning)
    Z > 3: Critical spike (alert)

Author: Gabriel Milhardo
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from src.database import Database


class AlertSeverity(Enum):
    """Alert severity levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """
    Represents an anomaly alert.

    Attributes:
        metric: Name of the metric (e.g., 'tpv', 'transactions')
        dimension: Dimension being analyzed (e.g., 'total', 'pix', 'pos')
        current_value: Current observed value
        expected_value: Expected value (rolling mean)
        z_score: Z-score value
        severity: Alert severity level
        change_pct: Percentage change from expected
        message: Human-readable alert message
    """
    metric: str
    dimension: str
    current_value: float
    expected_value: float
    z_score: float
    severity: AlertSeverity
    change_pct: float
    message: str


class AnomalyDetector:
    """
    Anomaly detection system using Z-score statistics.

    This class monitors transaction metrics and identifies unusual patterns
    that may indicate system issues, fraud, or significant business changes.

    Attributes:
        db: Database instance
        window: Rolling window size in days
        warning_threshold: Z-score threshold for warnings
        critical_threshold: Z-score threshold for critical alerts
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        window: int = 30,
        warning_threshold: float = 2.0,
        critical_threshold: float = 3.0
    ):
        """
        Initialize the anomaly detector.

        Args:
            db: Database instance
            window: Rolling window size (default: 30 days)
            warning_threshold: Z-score for warnings (default: 2.0)
            critical_threshold: Z-score for critical (default: 3.0)
        """
        if db is None:
            self.db = Database()
            self.db.load_csv_to_db()
        else:
            self.db = db

        self.window = window
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def _calculate_z_score(
        self,
        current: float,
        mean: float,
        std: float
    ) -> float:
        """
        Calculate Z-score for a value.

        Args:
            current: Current observed value
            mean: Historical mean
            std: Historical standard deviation

        Returns:
            Z-score value
        """
        if std == 0 or np.isnan(std):
            return 0.0
        return (current - mean) / std

    def _get_severity(self, z_score: float) -> AlertSeverity:
        """
        Determine severity based on Z-score.

        Args:
            z_score: Z-score value

        Returns:
            AlertSeverity enum
        """
        abs_z = abs(z_score)

        if abs_z >= self.critical_threshold:
            return AlertSeverity.CRITICAL
        elif abs_z >= self.warning_threshold:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.NORMAL

    def _format_message(
        self,
        metric: str,
        dimension: str,
        z_score: float,
        change_pct: float,
        current: float,
        expected: float
    ) -> str:
        """
        Generate human-readable alert message.

        Args:
            metric: Metric name
            dimension: Dimension name
            z_score: Z-score value
            change_pct: Percentage change
            current: Current value
            expected: Expected value

        Returns:
            Formatted message string
        """
        direction = "dropped" if z_score < 0 else "spiked"
        metric_label = metric.upper()

        if dimension == "total":
            dim_text = f"Total {metric_label}"
        else:
            dim_text = f"{metric_label} for {dimension.upper()}"

        return (
            f"{dim_text} {direction} {abs(change_pct):.1f}% "
            f"(Z-score: {z_score:.2f}). "
            f"Current: R$ {current:,.2f}, Expected: R$ {expected:,.2f}"
        )

    def check_total_tpv(self) -> Alert:
        """
        Check total TPV for anomalies.

        Returns:
            Alert object with analysis results
        """
        # Get daily TPV
        df = self.db.execute_query("""
            SELECT day, SUM(amount_transacted) as tpv
            FROM transactions
            GROUP BY day
            ORDER BY day
        """)

        df['day'] = pd.to_datetime(df['day'])
        df = df.sort_values('day')

        # Calculate rolling statistics
        df['rolling_mean'] = df['tpv'].rolling(window=self.window).mean()
        df['rolling_std'] = df['tpv'].rolling(window=self.window).std()

        # Get latest values
        latest = df.iloc[-1]
        prev_mean = df.iloc[-2]['rolling_mean'] if len(df) > 1 else latest['rolling_mean']
        prev_std = df.iloc[-2]['rolling_std'] if len(df) > 1 else latest['rolling_std']

        current = latest['tpv']
        expected = prev_mean

        # Calculate Z-score
        z_score = self._calculate_z_score(current, expected, prev_std)
        severity = self._get_severity(z_score)
        change_pct = ((current - expected) / expected) * 100 if expected else 0

        return Alert(
            metric="tpv",
            dimension="total",
            current_value=current,
            expected_value=expected,
            z_score=z_score,
            severity=severity,
            change_pct=change_pct,
            message=self._format_message("tpv", "total", z_score, change_pct, current, expected)
        )

    def check_tpv_by_product(self) -> List[Alert]:
        """
        Check TPV by product for anomalies.

        Returns:
            List of Alert objects, one per product
        """
        alerts = []

        # Get list of products
        products = self.db.get_unique_values("product")

        for product in products:
            # Get daily TPV for this product
            df = self.db.execute_query(f"""
                SELECT day, SUM(amount_transacted) as tpv
                FROM transactions
                WHERE product = '{product}'
                GROUP BY day
                ORDER BY day
            """)

            df['day'] = pd.to_datetime(df['day'])
            df = df.sort_values('day')

            # Calculate rolling statistics
            df['rolling_mean'] = df['tpv'].rolling(window=self.window).mean()
            df['rolling_std'] = df['tpv'].rolling(window=self.window).std()

            # Get latest values
            latest = df.iloc[-1]
            prev_mean = df.iloc[-2]['rolling_mean'] if len(df) > 1 else latest['rolling_mean']
            prev_std = df.iloc[-2]['rolling_std'] if len(df) > 1 else latest['rolling_std']

            current = latest['tpv']
            expected = prev_mean

            # Calculate Z-score
            z_score = self._calculate_z_score(current, expected, prev_std)
            severity = self._get_severity(z_score)
            change_pct = ((current - expected) / expected) * 100 if expected else 0

            alerts.append(Alert(
                metric="tpv",
                dimension=product,
                current_value=current,
                expected_value=expected,
                z_score=z_score,
                severity=severity,
                change_pct=change_pct,
                message=self._format_message("tpv", product, z_score, change_pct, current, expected)
            ))

        return alerts

    def check_transactions(self) -> Alert:
        """
        Check transaction count for anomalies.

        Returns:
            Alert object with analysis results
        """
        df = self.db.execute_query("""
            SELECT day, SUM(quantity_transactions) as txns
            FROM transactions
            GROUP BY day
            ORDER BY day
        """)

        df['day'] = pd.to_datetime(df['day'])
        df = df.sort_values('day')

        df['rolling_mean'] = df['txns'].rolling(window=self.window).mean()
        df['rolling_std'] = df['txns'].rolling(window=self.window).std()

        latest = df.iloc[-1]
        prev_mean = df.iloc[-2]['rolling_mean'] if len(df) > 1 else latest['rolling_mean']
        prev_std = df.iloc[-2]['rolling_std'] if len(df) > 1 else latest['rolling_std']

        current = latest['txns']
        expected = prev_mean

        z_score = self._calculate_z_score(current, expected, prev_std)
        severity = self._get_severity(z_score)
        change_pct = ((current - expected) / expected) * 100 if expected else 0

        message = (
            f"Transaction count {'dropped' if z_score < 0 else 'spiked'} {abs(change_pct):.1f}% "
            f"(Z-score: {z_score:.2f}). "
            f"Current: {current:,.0f}, Expected: {expected:,.0f}"
        )

        return Alert(
            metric="transactions",
            dimension="total",
            current_value=current,
            expected_value=expected,
            z_score=z_score,
            severity=severity,
            change_pct=change_pct,
            message=message
        )

    def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all anomaly checks and return comprehensive results.

        Returns:
            Dictionary with all alerts and summary
        """
        results = {
            "total_tpv": self.check_total_tpv(),
            "transactions": self.check_transactions(),
            "by_product": self.check_tpv_by_product(),
            "summary": {
                "total_alerts": 0,
                "critical": 0,
                "warning": 0,
                "normal": 0
            }
        }

        # Count alerts by severity
        all_alerts = [results["total_tpv"], results["transactions"]] + results["by_product"]

        for alert in all_alerts:
            results["summary"]["total_alerts"] += 1
            if alert.severity == AlertSeverity.CRITICAL:
                results["summary"]["critical"] += 1
            elif alert.severity == AlertSeverity.WARNING:
                results["summary"]["warning"] += 1
            else:
                results["summary"]["normal"] += 1

        return results

    def get_alerts_for_display(self) -> List[Dict[str, Any]]:
        """
        Get alerts formatted for UI display.

        Returns:
            List of alert dictionaries with display-ready data
        """
        results = self.run_all_checks()
        all_alerts = [results["total_tpv"], results["transactions"]] + results["by_product"]

        display_alerts = []
        for alert in all_alerts:
            display_alerts.append({
                "metric": alert.metric,
                "dimension": alert.dimension,
                "severity": alert.severity.value,
                "change_pct": alert.change_pct,
                "z_score": alert.z_score,
                "message": alert.message,
                "icon": self._get_icon(alert.severity),
                "color": self._get_color(alert.severity)
            })

        # Sort by severity (critical first)
        severity_order = {"critical": 0, "warning": 1, "normal": 2}
        display_alerts.sort(key=lambda x: severity_order[x["severity"]])

        return display_alerts

    def _get_icon(self, severity: AlertSeverity) -> str:
        """Get icon for severity level."""
        icons = {
            AlertSeverity.CRITICAL: "[!!!]",
            AlertSeverity.WARNING: "[!]",
            AlertSeverity.NORMAL: "[OK]"
        }
        return icons[severity]

    def _get_color(self, severity: AlertSeverity) -> str:
        """Get color for severity level."""
        colors = {
            AlertSeverity.CRITICAL: "red",
            AlertSeverity.WARNING: "orange",
            AlertSeverity.NORMAL: "green"
        }
        return colors[severity]


# Convenience function
def check_anomalies() -> List[Dict[str, Any]]:
    """
    Quick check for all anomalies.

    Returns:
        List of alert dictionaries
    """
    detector = AnomalyDetector()
    return detector.get_alerts_for_display()


# For direct testing
if __name__ == "__main__":
    print("=" * 60)
    print("ANOMALY DETECTION TEST")
    print("=" * 60)

    detector = AnomalyDetector()

    # Run all checks
    results = detector.run_all_checks()

    # Print summary
    print(f"\nSummary:")
    print(f"  Total checks: {results['summary']['total_alerts']}")
    print(f"  Critical: {results['summary']['critical']}")
    print(f"  Warning: {results['summary']['warning']}")
    print(f"  Normal: {results['summary']['normal']}")

    # Print total TPV alert
    print(f"\n{'='*60}")
    print("Total TPV Alert:")
    print(f"  {results['total_tpv'].message}")

    # Print transaction alert
    print(f"\n{'='*60}")
    print("Transaction Count Alert:")
    print(f"  {results['transactions'].message}")

    # Print product alerts
    print(f"\n{'='*60}")
    print("Product Alerts:")
    for alert in results['by_product']:
        icon = "[!!!]" if alert.severity == AlertSeverity.CRITICAL else "[!]" if alert.severity == AlertSeverity.WARNING else "[OK]"
        print(f"  {icon} {alert.dimension}: {alert.change_pct:+.1f}% (Z={alert.z_score:.2f})")

    print("\n[OK] Anomaly detection test completed!")
