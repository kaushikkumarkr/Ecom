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

def run_quality_check():
    print("Starting Great Expectations Check (GE 1.10.0 API)...")
    
    context = gx.get_context()
    
    # Define Datasource
    datasource_name = "my_postgres"
    # Try to get or add
    try:
        ds = context.data_sources.get(datasource_name)
    except:
        ds = context.data_sources.add_postgres(
            name=datasource_name,
            connection_string=connection_string
        )
        
    # Define Asset
    asset_name = "raw_users"
    try:
        asset = ds.get_asset(asset_name)
    except:
        asset = ds.add_table_asset(
            name=asset_name,
            table_name="users",
            schema_name="raw"
        )
        
    # Define Batch Definition
    batch_def_name = "default_batch_def"
    try:
        batch_def = asset.get_batch_definition(batch_def_name)
    except:
        batch_def = asset.add_batch_definition(name=batch_def_name)
        
    # Define Suite
    suite_name = "users_suite"
    try:
        suite = context.suites.get(suite_name)
    except:
        suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
        # Add Expectations
        suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=1, max_value=10000000))
        suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="id"))
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="id"))
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="email", mostly=0.9))

    # Define Validation Definition
    val_def_name = "users_validation"
    try:
        val_def = context.validation_definitions.get(val_def_name)
    except:
        val_def = context.validation_definitions.add(
            gx.ValidationDefinition(name=val_def_name, data=batch_def, suite=suite)
        )

    # Define Checkpoint
    checkpoint_name = "users_checkpoint"
    try:
        checkpoint = context.checkpoints.get(checkpoint_name)
    except:
        checkpoint = context.checkpoints.add(
            gx.Checkpoint(name=checkpoint_name, validation_definitions=[val_def])
        )

    # Run
    print("Running Checkpoint...")
    results = checkpoint.run()
    
    # Check results
    success = results.success
    print(f"Success: {success}")
    
    if not success:
        print("Data Quality Check FAILED!")
        # Print details
        for result in results.run_results.values():
            if not result["success"]:
                print(result)
        sys.exit(1)
    else:
        print("Data Quality Check PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    run_quality_check()
