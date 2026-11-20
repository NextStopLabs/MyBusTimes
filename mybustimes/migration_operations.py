"""Migration operations that avoid blocking production tables on PostgreSQL.

Removing a field's ``db_index`` makes ``AlterField`` run ``DROP INDEX``, which
takes an ``ACCESS EXCLUSIVE`` lock on the table and can wait behind live
traffic until the 30s statement timeout fires.  These operations update the
migration state normally but drop the index with ``DROP INDEX CONCURRENTLY`` on
PostgreSQL, which keeps the table writable while the index is removed.

Migrations using them must set ``atomic = False`` because ``CONCURRENTLY``
cannot run inside a transaction block.
"""

from django.db import migrations


class PostgresOnlyRunSQL(migrations.RunSQL):
    """Run SQL only on PostgreSQL, so local SQLite databases can migrate."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "postgresql":
            super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "postgresql":
            super().database_backwards(app_label, schema_editor, from_state, to_state)


def disable_timeouts():
    """Let concurrent index drops wait for in-flight transactions to finish."""
    return [
        PostgresOnlyRunSQL(
            "SET statement_timeout = 0", reverse_sql=migrations.RunSQL.noop
        ),
        PostgresOnlyRunSQL(
            "SET lock_timeout = 0", reverse_sql=migrations.RunSQL.noop
        ),
    ]


def restore_timeouts():
    return [
        PostgresOnlyRunSQL(
            "RESET lock_timeout", reverse_sql=migrations.RunSQL.noop
        ),
        PostgresOnlyRunSQL(
            "RESET statement_timeout", reverse_sql=migrations.RunSQL.noop
        ),
    ]


def _model_state(state, app_label, model_name_lower):
    return state.models[app_label, model_name_lower]


def _table_name(model_state):
    return model_state.options.get("db_table") or (
        f"{model_state.app_label}_{model_state.name_lower}"
    )


class RemoveFieldIndexConcurrently(migrations.AlterField):
    """``AlterField`` that drops the old field index concurrently.

    This is intended for migrations where the only database change is removing
    ``db_index``.  Other field changes still go through the regular
    ``AlterField`` path.
    """

    def _index_name(self, schema_editor, model_state, field):
        return schema_editor._create_index_name(
            _table_name(model_state), [field.column]
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return super().database_forwards(
                app_label, schema_editor, from_state, to_state
            )

        from_field = _model_state(
            from_state, app_label, self.model_name_lower
        ).fields[self.name]
        to_model = _model_state(to_state, app_label, self.model_name_lower)
        to_field = to_model.fields[self.name]

        if (
            from_field.db_index
            and not to_field.db_index
            and not to_field.primary_key
            and not to_field.unique
        ):
            index_name = self._index_name(schema_editor, to_model, to_field)
            schema_editor.execute(
                "DROP INDEX CONCURRENTLY IF EXISTS "
                f"{schema_editor.quote_name(index_name)}"
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return super().database_backwards(
                app_label, schema_editor, from_state, to_state
            )

        from_field = _model_state(
            from_state, app_label, self.model_name_lower
        ).fields[self.name]
        to_model = _model_state(to_state, app_label, self.model_name_lower)
        to_field = to_model.fields[self.name]

        if (
            to_field.db_index
            and not from_field.db_index
            and not to_field.primary_key
            and not to_field.unique
        ):
            table_name = schema_editor.quote_name(_table_name(to_model))
            column_name = schema_editor.quote_name(to_field.column)
            index_name = self._index_name(schema_editor, to_model, to_field)
            schema_editor.execute(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                f"{schema_editor.quote_name(index_name)} "
                f"ON {table_name} ({column_name})"
            )


class RemoveIndexConcurrently(migrations.RemoveIndex):
    """``RemoveIndex`` that drops the index concurrently on PostgreSQL."""

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return super().database_forwards(
                app_label, schema_editor, from_state, to_state
            )

        schema_editor.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS "
            f"{schema_editor.quote_name(self.name)}"
        )
