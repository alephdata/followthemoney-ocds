# followthemoney-ocds

Import data formatted as OpenContracting Data Standard (OCDS) JSON object
streams into FollowTheMoney objects. FtM is much less verbose in describing
procurment processes, so we're collating the complex process information 
in OCDS into `Contract` and `ContractAward` objects.

**Note:** This importer doesn't aim to strictly implement the OCDS spec, but
rather capture the variety of OCDS-style data releases available in the wild.