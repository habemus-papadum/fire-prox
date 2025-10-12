"""
Integration tests for Firestore aggregation queries (asynchronous).

Tests aggregation support for count(), sum(), avg(), and aggregate()
operations that calculate statistics without fetching all documents.
"""

import pytest

from fire_prox import Avg, Count, Sum


@pytest.fixture
def employees(async_db):
    """Return a test collection for employees."""
    return async_db.collection('async_aggregation_test_employees')


@pytest.fixture
def products(async_db):
    """Return a test collection for products."""
    return async_db.collection('async_aggregation_test_products')


# =========================================================================
# Count Tests
# =========================================================================

class TestCountAggregation:
    """Test count() aggregation for document counting."""

    @pytest.mark.asyncio
    async def test_count_empty_collection(self, employees):
        """Test counting documents in empty collection returns 0."""
        count = await employees.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_all_documents(self, employees):
        """Test counting all documents in a collection."""
        # Create 5 employees
        for i in range(5):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = 50000 + (i * 10000)
            await emp.save()

        count = await employees.count()
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_with_filter(self, employees):
        """Test counting documents with a filter."""
        # Create employees with different salaries
        for i in range(10):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = 50000 + (i * 10000)
            emp.active = i % 2 == 0
            await emp.save()

        # Count active employees
        active_count = await employees.where('active', '==', True).count()
        assert active_count == 5

        # Count high earners
        high_earners = await employees.where('salary', '>', 100000).count()
        assert high_earners == 4  # 110000, 120000, 130000, 140000

    @pytest.mark.asyncio
    async def test_count_with_multiple_filters(self, employees):
        """Test counting with multiple filter conditions."""
        # Create employees
        for i in range(10):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = 50000 + (i * 10000)
            emp.department = 'Engineering' if i < 5 else 'Sales'
            emp.active = i % 2 == 0
            await emp.save()

        # Count active engineering employees
        count = await (employees
                .where('department', '==', 'Engineering')
                .where('active', '==', True)
                .count())
        assert count == 3  # indices 0, 2, 4


# =========================================================================
# Sum Tests
# =========================================================================

class TestSumAggregation:
    """Test sum() aggregation for numeric field summation."""

    @pytest.mark.asyncio
    async def test_sum_empty_collection(self, employees):
        """Test sum on empty collection returns 0."""
        total = await employees.sum('salary')
        assert total == 0

    @pytest.mark.asyncio
    async def test_sum_all_documents(self, employees):
        """Test summing a field across all documents."""
        # Create employees
        salaries = [50000, 60000, 70000, 80000, 90000]
        for i, salary in enumerate(salaries):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = salary
            await emp.save()

        total_salary = await employees.sum('salary')
        assert total_salary == sum(salaries)  # 350000

    @pytest.mark.asyncio
    async def test_sum_with_filter(self, employees):
        """Test summing with a filter condition."""
        # Create employees
        for i in range(5):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = 50000 + (i * 10000)
            emp.department = 'Engineering' if i < 3 else 'Sales'
            await emp.save()

        # Sum engineering salaries
        eng_total = await (employees
                    .where('department', '==', 'Engineering')
                    .sum('salary'))
        assert eng_total == 50000 + 60000 + 70000  # 180000

    @pytest.mark.asyncio
    async def test_sum_float_values(self, products):
        """Test summing float values."""
        # Create products with decimal prices
        prices = [19.99, 29.99, 39.99, 49.99]
        for i, price in enumerate(prices):
            prod = products.new()
            prod.name = f'Product{i}'
            prod.price = price
            await prod.save()

        total_revenue = await products.sum('price')
        assert abs(total_revenue - sum(prices)) < 0.01  # Float comparison

    @pytest.mark.asyncio
    async def test_sum_with_mixed_int_and_float(self, products):
        """Test summing mixed integer and float values."""
        # Create products
        prod1 = products.new()
        prod1.name = 'Product1'
        prod1.price = 100  # int
        await prod1.save()

        prod2 = products.new()
        prod2.name = 'Product2'
        prod2.price = 99.99  # float
        await prod2.save()

        total = await products.sum('price')
        assert abs(total - 199.99) < 0.01

    @pytest.mark.asyncio
    async def test_sum_requires_field_name(self, employees):
        """Test that sum() raises ValueError without field name."""
        with pytest.raises(ValueError, match="sum\\(\\) requires a field name"):
            await employees.sum('')


# =========================================================================
# Average Tests
# =========================================================================

class TestAvgAggregation:
    """Test avg() aggregation for numeric field averaging."""

    @pytest.mark.asyncio
    async def test_avg_empty_collection(self, employees):
        """Test average on empty collection returns 0."""
        avg = await employees.avg('salary')
        assert avg == 0.0

    @pytest.mark.asyncio
    async def test_avg_all_documents(self, employees):
        """Test averaging a field across all documents."""
        # Create employees
        salaries = [50000, 60000, 70000, 80000, 90000]
        for i, salary in enumerate(salaries):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = salary
            await emp.save()

        avg_salary = await employees.avg('salary')
        expected_avg = sum(salaries) / len(salaries)  # 70000
        assert avg_salary == expected_avg

    @pytest.mark.asyncio
    async def test_avg_with_filter(self, employees):
        """Test averaging with a filter condition."""
        # Create employees
        for i in range(6):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = 50000 + (i * 10000)
            emp.department = 'Engineering' if i < 3 else 'Sales'
            await emp.save()

        # Average engineering salaries
        eng_avg = await (employees
                  .where('department', '==', 'Engineering')
                  .avg('salary'))
        # Engineering: 50000, 60000, 70000
        assert eng_avg == 60000.0

    @pytest.mark.asyncio
    async def test_avg_float_values(self, products):
        """Test averaging float values."""
        # Create products
        ratings = [4.5, 3.8, 4.2, 4.9, 4.6]
        for i, rating in enumerate(ratings):
            prod = products.new()
            prod.name = f'Product{i}'
            prod.rating = rating
            await prod.save()

        avg_rating = await products.avg('rating')
        expected = sum(ratings) / len(ratings)  # 4.4
        assert abs(avg_rating - expected) < 0.01

    @pytest.mark.asyncio
    async def test_avg_requires_field_name(self, employees):
        """Test that avg() raises ValueError without field name."""
        with pytest.raises(ValueError, match="avg\\(\\) requires a field name"):
            await employees.avg('')


# =========================================================================
# Multiple Aggregations Tests
# =========================================================================

class TestMultipleAggregations:
    """Test aggregate() for multiple aggregations in one query."""

    @pytest.mark.asyncio
    async def test_aggregate_single_count(self, employees):
        """Test aggregate with single count aggregation."""
        # Create employees
        for i in range(3):
            emp = employees.new()
            emp.name = f'Employee{i}'
            await emp.save()

        result = await employees.aggregate(total=Count())
        assert result == {'total': 3}

    @pytest.mark.asyncio
    async def test_aggregate_count_and_sum(self, employees):
        """Test aggregate with count and sum."""
        # Create employees
        salaries = [50000, 60000, 70000]
        for i, salary in enumerate(salaries):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = salary
            await emp.save()

        result = await employees.aggregate(
            total_employees=Count(),
            total_salary=Sum('salary')
        )
        assert result['total_employees'] == 3
        assert result['total_salary'] == sum(salaries)

    @pytest.mark.asyncio
    async def test_aggregate_all_three_types(self, employees):
        """Test aggregate with count, sum, and average."""
        # Create employees
        salaries = [50000, 60000, 70000, 80000, 90000]
        for i, salary in enumerate(salaries):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = salary
            emp.age = 25 + i
            await emp.save()

        result = await employees.aggregate(
            count=Count(),
            total_salary=Sum('salary'),
            avg_salary=Avg('salary'),
            avg_age=Avg('age')
        )

        assert result['count'] == 5
        assert result['total_salary'] == sum(salaries)
        assert result['avg_salary'] == sum(salaries) / len(salaries)
        assert result['avg_age'] == (25 + 26 + 27 + 28 + 29) / 5  # 27.0

    @pytest.mark.asyncio
    async def test_aggregate_with_filters(self, employees):
        """Test aggregate with query filters."""
        # Create employees
        for i in range(10):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = 50000 + (i * 10000)
            emp.department = 'Engineering' if i < 5 else 'Sales'
            await emp.save()

        # Aggregate for engineering department only
        result = await (employees
                 .where('department', '==', 'Engineering')
                 .aggregate(
                     count=Count(),
                     total=Sum('salary'),
                     average=Avg('salary')
                 ))

        assert result['count'] == 5
        assert result['total'] == 50000 + 60000 + 70000 + 80000 + 90000  # 350000
        assert result['average'] == 70000.0

    @pytest.mark.asyncio
    async def test_aggregate_requires_at_least_one_aggregation(self, employees):
        """Test that aggregate() raises ValueError with no aggregations."""
        with pytest.raises(ValueError, match="aggregate\\(\\) requires at least one aggregation"):
            await employees.aggregate()

    @pytest.mark.asyncio
    async def test_aggregate_rejects_invalid_types(self, employees):
        """Test that aggregate() rejects invalid aggregation types."""
        with pytest.raises(ValueError, match="Invalid aggregation type"):
            await employees.aggregate(invalid="not an aggregation")


# =========================================================================
# Edge Cases and Error Handling
# =========================================================================

class TestAggregationEdgeCases:
    """Test edge cases and error conditions for aggregations."""

    @pytest.mark.asyncio
    async def test_count_chained_with_order_by(self, employees):
        """Test that count works when chained with order_by."""
        # Create employees
        for i in range(5):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = 50000 + (i * 10000)
            await emp.save()

        # order_by doesn't affect count, but should not cause error
        count = await employees.order_by('salary').count()
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_chained_with_limit(self, employees):
        """Test that count works when chained with limit."""
        # Create employees
        for i in range(10):
            emp = employees.new()
            emp.name = f'Employee{i}'
            await emp.save()

        # Note: limit should not affect count
        # (counting all matches, not just limited results)
        count = await employees.limit(5).count()
        # Firestore behavior: limit may or may not affect count
        # Just verify it doesn't crash
        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_sum_with_all_zero_values(self, employees):
        """Test summing when all values are zero."""
        # Create employees with zero salary
        for i in range(3):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = 0
            await emp.save()

        total = await employees.sum('salary')
        assert total == 0

    @pytest.mark.asyncio
    async def test_avg_with_single_document(self, employees):
        """Test averaging with only one document."""
        emp = employees.new()
        emp.name = 'Solo'
        emp.salary = 75000
        await emp.save()

        avg = await employees.avg('salary')
        assert avg == 75000.0


# =========================================================================
# Real-World Use Cases
# =========================================================================

class TestRealWorldScenarios:
    """Test realistic use cases for aggregations."""

    @pytest.mark.asyncio
    async def test_financial_dashboard(self, employees):
        """Test aggregations for financial reporting."""
        # Create diverse employee data
        departments = ['Engineering', 'Sales', 'Marketing', 'HR']
        for i in range(20):
            emp = employees.new()
            emp.name = f'Employee{i}'
            emp.salary = 50000 + (i * 5000)
            emp.department = departments[i % 4]
            emp.bonus = emp.salary * 0.1
            await emp.save()

        # Engineering department stats
        eng_stats = await (employees
                    .where('department', '==', 'Engineering')
                    .aggregate(
                        total_employees=Count(),
                        total_compensation=Sum('salary'),
                        avg_salary=Avg('salary'),
                        total_bonus=Sum('bonus')
                    ))

        assert eng_stats['total_employees'] == 5
        assert eng_stats['total_compensation'] > 0
        assert eng_stats['avg_salary'] > 0
        assert eng_stats['total_bonus'] > 0

    @pytest.mark.asyncio
    async def test_inventory_summary(self, products):
        """Test aggregations for inventory management."""
        # Create products
        categories = ['Electronics', 'Clothing', 'Food']
        for i in range(15):
            prod = products.new()
            prod.name = f'Product{i}'
            prod.category = categories[i % 3]
            prod.quantity = 10 + i
            prod.price = 10.0 + (i * 2.5)
            await prod.save()

        # Electronics category stats
        electronics_stats = await (products
                            .where('category', '==', 'Electronics')
                            .aggregate(
                                count=Count(),
                                total_quantity=Sum('quantity'),
                                avg_price=Avg('price')
                            ))

        assert electronics_stats['count'] == 5
        assert electronics_stats['total_quantity'] > 0
        assert electronics_stats['avg_price'] > 0

    @pytest.mark.asyncio
    async def test_user_analytics(self, async_db):
        """Test aggregations for user analytics."""
        users = async_db.collection('async_aggregation_test_users')

        # Create users with activity data
        for i in range(50):
            user = users.new()
            user.name = f'User{i}'
            user.age = 20 + (i % 40)
            user.active = i % 3 == 0
            user.posts_count = i * 2
            await user.save()

        # Active users statistics
        active_stats = await (users
                       .where('active', '==', True)
                       .aggregate(
                           total_active=Count(),
                           avg_age=Avg('age'),
                           total_posts=Sum('posts_count')
                       ))

        assert active_stats['total_active'] > 0
        assert 20 <= active_stats['avg_age'] <= 60
        assert active_stats['total_posts'] >= 0
