import great_expectations as gx
import great_expectations.expectations as gxe
import os
import sys

# Ensure we have env vars
db_user = os.getenv('POSTGRES_USER', 'user')
db_pass = os.getenv('POSTGRES_PASSWORD', 'password')
db_host = os.getenv('POSTGRES_HOST', 'postgres')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_name = os.getenv('POSTGRES_DB', 'ecom')

connection_string = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

def add_validation(context, ds, asset_name, table_name, schema_name, suite_name, expectations):
    # Get/Add Asset
    try:
        asset = ds.get_asset(asset_name)
    except:
        asset = ds.add_table_asset(
            name=asset_name,
            table_name=table_name,
            schema_name=schema_name
        )
        
    # Get/Add Batch Def
    batch_def_name = f"{asset_name}_batch_def"
    try:
        batch_def = asset.get_batch_definition(batch_def_name)
    except:
        batch_def = asset.add_batch_definition(name=batch_def_name)

    # Get/Add Suite
    try:
        suite = context.suites.get(suite_name)
    except:
        suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
        for exp in expectations:
            suite.add_expectation(exp)
            
    # Get/Add Val Def
    val_def_name = f"{asset_name}_validation"
    try:
        val_def = context.validation_definitions.get(val_def_name)
    except:
        val_def = context.validation_definitions.add(
            gx.ValidationDefinition(name=val_def_name, data=batch_def, suite=suite)
        )
    return val_def

def run_quality_check():
    print("Starting Great Expectations Check (GE 1.10.0 API)...")
    context = gx.get_context()
    
    # Datasource
    datasource_name = "my_postgres"
    try:
        ds = context.data_sources.get(datasource_name)
    except:
        ds = context.data_sources.add_postgres(
            name=datasource_name,
            connection_string=connection_string
        )

    validations_to_run = []

    # 1. Raw Users Check
    validations_to_run.append(add_validation(
        context, ds, "raw_users", "users", "raw", "users_suite",
        [
            gxe.ExpectTableRowCountToBeBetween(min_value=1, max_value=10000000),
            gxe.ExpectColumnValuesToBeUnique(column="id"),
            gxe.ExpectColumnValuesToNotBeNull(column="email", mostly=0.9)
        ]
    ))

    # 2. Churn Features Check (Sprint 1)
    validations_to_run.append(add_validation(
        context, ds, "churn_features", "churn_features", "public_marts", "churn_features_suite",
        [
            gxe.ExpectTableRowCountToBeBetween(min_value=1000, max_value=1000000), # Expect at least 1k users
            gxe.ExpectColumnValuesToBeUnique(column="user_id"),
            gxe.ExpectColumnValuesToNotBeNull(column="recency_days"),
            gxe.ExpectColumnValuesToNotBeNull(column="frequency_60d")
        ]
    ))

    # Checkpoint
    checkpoint_name = "ecom_checkpoint"
    try:
        checkpoint = context.checkpoints.get(checkpoint_name)
        # Update endpoint definitions if needed, but easiest to just reuse or recreate.
        # Checkpoint definitions are additive if we are careful, but here let's simplify.
        # Ideally we update the validation_definitions list.
        checkpoint.validation_definitions = validations_to_run
    except:
        checkpoint = context.checkpoints.add(
            gx.Checkpoint(name=checkpoint_name, validation_definitions=validations_to_run)
        )

    # Run
    print("Running Checkpoint...")
    results = checkpoint.run()
    
    success = results.success
    print(f"Overall Success: {success}")
    
    if not success:
        print("Data Quality Check FAILED!")
        for res in results.run_results.values():
            if not res["success"]:
                print(f"Failed Validation: {res['validation_result']['meta']}")
        sys.exit(1)
    else:
        print("Data Quality Check PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    run_quality_check()
