using UnrealBuildTool;

public class SifuModTools : ModuleRules
{
	public SifuModTools(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[] {
			"UnrealEd", "Json", "JsonUtilities", "PhysicsCore",
			"ClothingSystemRuntimeInterface", "ClothingSystemRuntimeCommon", "ClothingSystemRuntimeNv",
			"ClothingSystemEditor", "ClothingSystemEditorInterface", "AssetRegistry",
			"BlueprintGraph", "Kismet", "KismetCompiler", "AnimGraphRuntime"
		});
	}
}
