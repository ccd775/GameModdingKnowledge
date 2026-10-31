using UnrealBuildTool;

public class PBZModTools : ModuleRules
{
	public PBZModTools(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[] {
			"UnrealEd", "Json", "JsonUtilities", "PhysicsCore", "PhysicsUtilities", "AssetRegistry",
			"BlueprintGraph", "Kismet", "KismetCompiler", "AnimGraph", "AnimGraphRuntime",
			"ClothingSystemRuntimeInterface", "ClothingSystemRuntimeCommon", "ClothingSystemEditor", "ClothingSystemEditorInterface", "ChaosCloth"
		});
	}
}
