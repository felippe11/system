import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context
from alembic import op as alembic_op
from alembic.operations import batch as alembic_batch
from alembic.operations import ops as alembic_ops
import sqlalchemy as sa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    def _install_safe_operations():
        """Monkeypatch Alembic ops to be idempotent for duplicate objects."""

        def _get_inspector():
            bind = alembic_op.get_bind()
            if bind is None:
                return None
            return sa.inspect(bind)

        def _table_exists(inspector, name, schema=None):
            if inspector is None:
                return False
            return inspector.has_table(name, schema=schema)

        def _column_exists(inspector, table_name, column_name, schema=None):
            if inspector is None:
                return False
            cols = inspector.get_columns(table_name, schema=schema)
            return any(col["name"] == column_name for col in cols)

        def _index_exists(inspector, table_name, index_name, schema=None):
            if inspector is None:
                return False
            indexes = inspector.get_indexes(table_name, schema=schema)
            return any(idx["name"] == index_name for idx in indexes)

        def _constraint_exists(inspector, table_name, constraint_name, schema=None):
            if inspector is None:
                return False
            fks = inspector.get_foreign_keys(table_name, schema=schema)
            uniques = inspector.get_unique_constraints(table_name, schema=schema)
            pk = inspector.get_pk_constraint(table_name, schema=schema) or {}
            if any(fk["name"] == constraint_name for fk in fks):
                return True
            if any(uc["name"] == constraint_name for uc in uniques):
                return True
            return pk.get("name") == constraint_name

        # ---- alembic.op wrappers ----
        _create_table = alembic_op.create_table
        _drop_table = alembic_op.drop_table
        _add_column = alembic_op.add_column
        _drop_column = alembic_op.drop_column
        _create_index = alembic_op.create_index
        _drop_index = alembic_op.drop_index
        _create_fk = alembic_op.create_foreign_key
        _drop_constraint = alembic_op.drop_constraint
        _create_unique = alembic_op.create_unique_constraint

        def safe_create_table(name, *cols, **kw):
            inspector = _get_inspector()
            schema = kw.get("schema")
            if _table_exists(inspector, name, schema=schema):
                logger.warning("Skipping create_table for existing table: %s", name)
                return None
            return _create_table(name, *cols, **kw)

        def safe_drop_table(name, **kw):
            inspector = _get_inspector()
            schema = kw.get("schema")
            if not _table_exists(inspector, name, schema=schema):
                logger.warning("Skipping drop_table for missing table: %s", name)
                return None
            return _drop_table(name, **kw)

        def safe_add_column(table_name, column, **kw):
            inspector = _get_inspector()
            schema = kw.get("schema")
            if _column_exists(inspector, table_name, column.name, schema=schema):
                logger.warning(
                    "Skipping add_column for existing column: %s.%s",
                    table_name,
                    column.name,
                )
                return None
            return _add_column(table_name, column, **kw)

        def safe_drop_column(table_name, column_name, **kw):
            inspector = _get_inspector()
            schema = kw.get("schema")
            if not _column_exists(inspector, table_name, column_name, schema=schema):
                logger.warning(
                    "Skipping drop_column for missing column: %s.%s",
                    table_name,
                    column_name,
                )
                return None
            return _drop_column(table_name, column_name, **kw)

        def safe_create_index(index_name, table_name, columns, **kw):
            inspector = _get_inspector()
            schema = kw.get("schema")
            if _index_exists(inspector, table_name, index_name, schema=schema):
                logger.warning(
                    "Skipping create_index for existing index: %s on %s",
                    index_name,
                    table_name,
                )
                return None
            return _create_index(index_name, table_name, columns, **kw)

        def safe_drop_index(index_name, table_name=None, **kw):
            inspector = _get_inspector()
            schema = kw.get("schema")
            if table_name and not _index_exists(
                inspector, table_name, index_name, schema=schema
            ):
                logger.warning(
                    "Skipping drop_index for missing index: %s on %s",
                    index_name,
                    table_name,
                )
                return None
            return _drop_index(index_name, table_name=table_name, **kw)

        def safe_create_foreign_key(
            name,
            source_table,
            referent_table,
            local_cols,
            remote_cols,
            **kw,
        ):
            inspector = _get_inspector()
            schema = kw.get("source_schema")
            if _constraint_exists(inspector, source_table, name, schema=schema):
                logger.warning(
                    "Skipping create_foreign_key for existing constraint: %s on %s",
                    name,
                    source_table,
                )
                return None
            return _create_fk(
                name,
                source_table,
                referent_table,
                local_cols,
                remote_cols,
                **kw,
            )

        def safe_create_unique_constraint(name, table_name, columns, **kw):
            inspector = _get_inspector()
            schema = kw.get("schema")
            if _constraint_exists(inspector, table_name, name, schema=schema):
                logger.warning(
                    "Skipping create_unique_constraint for existing constraint: %s on %s",
                    name,
                    table_name,
                )
                return None
            return _create_unique(name, table_name, columns, **kw)

        def safe_drop_constraint(name, table_name, type_=None, **kw):
            inspector = _get_inspector()
            schema = kw.get("schema")
            if not _constraint_exists(inspector, table_name, name, schema=schema):
                logger.warning(
                    "Skipping drop_constraint for missing constraint: %s on %s",
                    name,
                    table_name,
                )
                return None
            return _drop_constraint(name, table_name, type_=type_, **kw)

        alembic_op.create_table = safe_create_table
        alembic_op.drop_table = safe_drop_table
        alembic_op.add_column = safe_add_column
        alembic_op.drop_column = safe_drop_column
        alembic_op.create_index = safe_create_index
        alembic_op.drop_index = safe_drop_index
        alembic_op.create_foreign_key = safe_create_foreign_key
        alembic_op.create_unique_constraint = safe_create_unique_constraint
        alembic_op.drop_constraint = safe_drop_constraint

        # ---- batch operations wrappers ----
        BatchOperations = getattr(alembic_batch, "BatchOperations", None)
        if BatchOperations is None:
            BatchOperations = getattr(alembic_ops, "BatchOperations", None)

        if BatchOperations is None:
            logger.warning("BatchOperations class not available; batch safety patch skipped.")
            return

        _batch_add_column = BatchOperations.add_column
        _batch_drop_column = BatchOperations.drop_column
        _batch_create_index = BatchOperations.create_index
        _batch_drop_index = BatchOperations.drop_index
        _batch_create_fk = BatchOperations.create_foreign_key
        _batch_drop_constraint = BatchOperations.drop_constraint
        _batch_create_unique = BatchOperations.create_unique_constraint

        def _batch_table_info(batch_self):
            table_name = getattr(batch_self, "table_name", None)
            schema = getattr(batch_self, "schema", None)
            if table_name is None and hasattr(batch_self, "impl"):
                table_name = getattr(batch_self.impl, "table_name", None)
                schema = schema or getattr(batch_self.impl, "schema", None)
            if table_name is None:
                table_name = getattr(batch_self, "_table_name", None)
            if schema is None:
                schema = getattr(batch_self, "_schema", None)
            return table_name, schema

        def safe_batch_add_column(self, column, **kw):
            inspector = _get_inspector()
            table_name, schema = _batch_table_info(self)
            if table_name is None:
                return _batch_add_column(self, column, **kw)
            if _column_exists(inspector, table_name, column.name, schema):
                logger.warning(
                    "Skipping batch add_column for existing column: %s.%s",
                    table_name,
                    column.name,
                )
                return None
            return _batch_add_column(self, column, **kw)

        def safe_batch_drop_column(self, column_name, **kw):
            inspector = _get_inspector()
            table_name, schema = _batch_table_info(self)
            if table_name is None:
                return _batch_drop_column(self, column_name, **kw)
            if not _column_exists(inspector, table_name, column_name, schema):
                logger.warning(
                    "Skipping batch drop_column for missing column: %s.%s",
                    table_name,
                    column_name,
                )
                return None
            return _batch_drop_column(self, column_name, **kw)

        def safe_batch_create_index(self, name, columns, **kw):
            inspector = _get_inspector()
            table_name, schema = _batch_table_info(self)
            if table_name is None:
                return _batch_create_index(self, name, columns, **kw)
            if _index_exists(inspector, table_name, name, schema):
                logger.warning(
                    "Skipping batch create_index for existing index: %s on %s",
                    name,
                    table_name,
                )
                return None
            return _batch_create_index(self, name, columns, **kw)

        def safe_batch_drop_index(self, name, **kw):
            inspector = _get_inspector()
            table_name, schema = _batch_table_info(self)
            if table_name is None:
                return _batch_drop_index(self, name, **kw)
            if not _index_exists(inspector, table_name, name, schema):
                logger.warning(
                    "Skipping batch drop_index for missing index: %s on %s",
                    name,
                    table_name,
                )
                return None
            return _batch_drop_index(self, name, **kw)

        def safe_batch_create_foreign_key(
            self,
            name,
            referent_table,
            local_cols,
            remote_cols,
            **kw,
        ):
            inspector = _get_inspector()
            table_name, schema = _batch_table_info(self)
            if table_name is None:
                return _batch_create_fk(
                    self,
                    name,
                    referent_table,
                    local_cols,
                    remote_cols,
                    **kw,
                )
            if _constraint_exists(inspector, table_name, name, schema):
                logger.warning(
                    "Skipping batch create_foreign_key for existing constraint: %s on %s",
                    name,
                    table_name,
                )
                return None
            return _batch_create_fk(
                self,
                name,
                referent_table,
                local_cols,
                remote_cols,
                **kw,
            )

        def safe_batch_create_unique_constraint(self, name, columns, **kw):
            inspector = _get_inspector()
            table_name, schema = _batch_table_info(self)
            if table_name is None:
                return _batch_create_unique(self, name, columns, **kw)
            if _constraint_exists(inspector, table_name, name, schema):
                logger.warning(
                    "Skipping batch create_unique_constraint for existing constraint: %s on %s",
                    name,
                    table_name,
                )
                return None
            return _batch_create_unique(self, name, columns, **kw)

        def safe_batch_drop_constraint(self, name, type_=None, **kw):
            inspector = _get_inspector()
            table_name, schema = _batch_table_info(self)
            if table_name is None:
                return _batch_drop_constraint(self, name, type_=type_, **kw)
            if not _constraint_exists(inspector, table_name, name, schema):
                logger.warning(
                    "Skipping batch drop_constraint for missing constraint: %s on %s",
                    name,
                    table_name,
                )
                return None
            return _batch_drop_constraint(self, name, type_=type_, **kw)

        BatchOperations.add_column = safe_batch_add_column
        BatchOperations.drop_column = safe_batch_drop_column
        BatchOperations.create_index = safe_batch_create_index
        BatchOperations.drop_index = safe_batch_drop_index
        BatchOperations.create_foreign_key = safe_batch_create_foreign_key
        BatchOperations.create_unique_constraint = safe_batch_create_unique_constraint
        BatchOperations.drop_constraint = safe_batch_drop_constraint

    with connectable.connect() as connection:
        _install_safe_operations()
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
