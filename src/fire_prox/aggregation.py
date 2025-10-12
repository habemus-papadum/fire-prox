"""
Aggregation helper classes for Firestore aggregation queries.

Provides Count, Sum, and Avg aggregation types that can be used
with FireQuery.aggregate() method for efficient analytics queries
without fetching all documents.

Example:
    from fire_prox.aggregation import Count, Sum, Avg

    # Single aggregation
    count = users.where('age', '>', 25).count()

    # Multiple aggregations
    stats = employees.aggregate(
        total=Count(),
        sum_salary=Sum('salary'),
        avg_age=Avg('age')
    )
"""

from typing import Optional


class AggregationType:
    """Base class for aggregation types."""

    def __init__(self, field: Optional[str] = None):
        """
        Initialize aggregation type.

        Args:
            field: Field name to aggregate (None for Count).
        """
        self.field = field

    def __repr__(self) -> str:
        """Return string representation."""
        if self.field:
            return f"{self.__class__.__name__}('{self.field}')"
        return f"{self.__class__.__name__}()"


class Count(AggregationType):
    """
    Count aggregation - counts matching documents.

    Does not require a field name since it counts documents, not field values.

    Example:
        # Count all active users
        count = users.where('active', '==', True).count()

        # Count via aggregate()
        result = users.aggregate(total_users=Count())
        # Returns: {'total_users': 42}
    """

    def __init__(self):
        """Initialize Count aggregation (no field needed)."""
        super().__init__(field=None)


class Sum(AggregationType):
    """
    Sum aggregation - sums a numeric field across documents.

    Requires a field name. The field must contain numeric values (int or float).

    Example:
        # Sum all salaries
        total = employees.sum('salary')

        # Sum via aggregate()
        result = employees.aggregate(total_revenue=Sum('revenue'))
        # Returns: {'total_revenue': 1500000}

    Args:
        field: Name of the numeric field to sum.

    Raises:
        ValueError: If field is not provided.
    """

    def __init__(self, field: str):
        """
        Initialize Sum aggregation.

        Args:
            field: Name of the numeric field to sum.

        Raises:
            ValueError: If field is None or empty.
        """
        if not field:
            raise ValueError("Sum aggregation requires a field name")
        super().__init__(field=field)


class Avg(AggregationType):
    """
    Average aggregation - averages a numeric field across documents.

    Requires a field name. The field must contain numeric values (int or float).
    Returns the arithmetic mean of all non-null values.

    Example:
        # Average age
        avg_age = users.avg('age')

        # Average via aggregate()
        result = users.aggregate(avg_rating=Avg('rating'))
        # Returns: {'avg_rating': 4.2}

    Args:
        field: Name of the numeric field to average.

    Raises:
        ValueError: If field is not provided.
    """

    def __init__(self, field: str):
        """
        Initialize Avg aggregation.

        Args:
            field: Name of the numeric field to average.

        Raises:
            ValueError: If field is None or empty.
        """
        if not field:
            raise ValueError("Avg aggregation requires a field name")
        super().__init__(field=field)
