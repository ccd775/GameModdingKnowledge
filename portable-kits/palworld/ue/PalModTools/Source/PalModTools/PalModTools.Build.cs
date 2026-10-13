using UnrealBuildTool;

public class PalModTools : ModuleRules
{
	public PalModTools(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[] { "UnrealEd", "BlueprintGraph", "AnimGraph", "AnimGraphRuntime", "Kismet" });
	}
}
