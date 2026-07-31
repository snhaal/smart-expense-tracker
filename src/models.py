"""Pydantic models for the Expense Tracker API."""

from datetime import date as date_type

from pydantic import BaseModel, Field, field_validator


class ExpenseCreate(BaseModel):
    """Payload for creating a new expense. The id is assigned by the server."""

    title: str = Field(..., min_length=1, description="Short description of the expense")
    amount: float = Field(..., gt=0, description="Expense amount, must be positive")
    category: str = Field(..., min_length=1, description="Category, e.g. Food, Travel, Rent")
    date: str = Field(..., description="Date in YYYY-MM-DD format")

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        try:
            parsed = date_type.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("date must be in YYYY-MM-DD format") from exc
        if parsed > date_type.today():
            raise ValueError("date cannot be in the future")
        return value


class Expense(ExpenseCreate):
    """An expense as stored and returned by the API, including its id."""

    id: int
