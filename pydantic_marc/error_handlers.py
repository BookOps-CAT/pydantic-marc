"""Error collection functions for `ControlField`, `DataField`, and `MarcRecord` models.

The validator functions in this module are used as either before or wrap validators
depending on the field and model.
"""

from __future__ import annotations

from typing import Any, Callable

from pydantic import ValidationError, ValidationInfo

from .errors import MarcCustomError


class MarcValidator:
    def __init__(self, error_provider: Callable) -> None:
        self.error_provider = error_provider
        self.validation_handler = ValidationHandler()

    def __call__(self, data: Any, info: ValidationInfo) -> Any:
        errors = self.error_provider(data=data, info=info)
        return self.validation_handler.raise_if_errors(errors=errors, data=data)


class MarcFieldValidator(MarcValidator):
    def __init__(self, error_func: Callable) -> None:
        super().__init__(self.rule_error_provider(error_func))

    def rule_error_provider(
        self, error_func: Callable[..., list[MarcCustomError]]
    ) -> Callable:
        def provider(*, data: Any, info: ValidationInfo) -> list[MarcCustomError]:
            rule = info.data.get("rules")
            tag = info.data.get("tag")
            if rule and isinstance(rule, dict) and "rules" in rule:
                rule = rule.get("rules", {}).get("LDR", {})
                tag = "LDR"
            elif rule and hasattr(rule, "rules"):
                rule = getattr(rule, "rules").get("LDR", {})
                tag = "LDR"
            if not rule:
                return []
            return error_func(rule=rule, data=data, tag=tag)

        return provider


class ValidationHandler:
    def raise_if_errors(self, errors: list[MarcCustomError], data: Any) -> Any:
        """
        Raise a `ValidationError` if any collected error details exist.

        This function takes a list of Pydantic `MarcCustomError` objects and raises a
        `ValidationError` if the list is not empty. Otherwise, it returns the validated
        data.

        Args:
            errors: a list of errors as `MarcCustomError` objects to raise, if any.
            data: the data object being validated (used as name in error context).

        Returns:
            The input data, validated, if no errors were raised.

        Raises:
            `ValidationError`: if errors were passed to the function via the
            `errors` arg.
        """
        if errors:
            raise ValidationError.from_exception_data(
                title=data.__class__.__name__,
                line_errors=[i.error_details for i in errors],
            )
        return data


class ErrorCollector:
    def collect_errors(
        self,
        validator: Callable[[Any, ValidationInfo], Any],
        data: Any,
        info: ValidationInfo,
    ) -> tuple[Any, list[MarcCustomError]]:
        """
        Execute a validator function and convert any errors raised to custom errors.

        This function wraps the execution of a validator, catching `ValidationError`
        exceptions and converting each error into a `MarcCustomError`. It returns the
        original or validated data along with a list of `MarcCustomError` used for
        raising or aggregating errors later.

        Args:
            validator: a callable validator function that takes `data` and `info`.
            data: the input data as a list to be validated.
            info: the `ValidationInfo` used during model validation.

        Returns:
            a tuple containing the validated data (or original data if invalid), and a
            list of `MarcCustomError` objects containing details about errors.
        """
        try:
            return validator(data, info), []
        except ValidationError as exc:
            errors = [
                MarcCustomError(e["type"], e["msg"], e["ctx"]) for e in exc.errors()
            ]
            return data, errors
