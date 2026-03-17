git checkout main
git rebase main bolt/pyarrow-as-py-optimization
git filter-repo --msg-filter '
if b"address remaining architecture policy violations" in message:
    return message.replace(b"ci: fix pip-audit invocation, address remaining architecture policy violations, and remove temp tracking files", b"ci: resolve CI checks including pip-audit, arch drift, and tracking issues")
return message
' --force
