// Headless graph authoring helpers exposed to editor Python (unreal.PalGraphLib). Port of SBGraphLib (UE 4.26) to UE 5.1.
// Graphs/nodes are passed as UObject so Python never needs wrappers for editor-only graph classes.
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "PalGraphLib.generated.h"

class UBlueprint;
class USkeletalMesh;
class USkeleton;

UCLASS()
class PALMODTOOLS_API UPalGraphLib : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Graph by name, searching function, ubergraph and implemented-interface graphs ("AnimGraph", "ClothLayer", ...). */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static UObject* GetGraph(UBlueprint* Blueprint, const FString& GraphName);

	/** "name|class|nodes=N" for every graph of the blueprint. */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static TArray<FString> ListGraphs(UBlueprint* Blueprint);

	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static TArray<UObject*> GetNodes(UObject* Graph);

	/** Spawns a node of the given class path (e.g. /Script/KawaiiPhysicsEd.AnimGraphNode_KawaiiPhysics). */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static UObject* AddNode(UObject* Graph, const FString& NodeClassPath, int32 X, int32 Y);

	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static bool RemoveNode(UObject* Node);

	/** One line per pin: "IN|OUT name category links default". */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static TArray<FString> GetPins(UObject* Node);

	/** Links an output pin to an input pin through the graph schema (pose-space conversion nodes are added as needed). */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static FString Connect(UObject* FromNode, const FString& FromPin, UObject* ToNode, const FString& ToPin);

	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static bool SetPinDefault(UObject* Node, const FString& PinName, const FString& Value);

	/** Sets a (nested) property from export text. Path: "Node.CapsuleLimits[2].DrivingBone"; arrays grow as needed. */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static bool SetProperty(UObject* Object, const FString& Path, const FString& Value);

	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static FString GetProperty(UObject* Object, const FString& Path);

	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static void Reconstruct(UObject* Node);

	/** Adds a member variable (PinCategory e.g. "float"); bInstanceEditable clears CPF_DisableEditOnInstance. */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static bool AddVariable(UBlueprint* Blueprint, FName Name, FName PinCategory, bool bInstanceEditable, const FString& DefaultValue);

	/** Implements an interface class (e.g. /Game/.../ALI_HumanCloth.ALI_HumanCloth_C); anim layer graphs are created. */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static bool ImplementInterface(UBlueprint* Blueprint, const FString& InterfaceClassPath);

	/** Adds an animation layer graph (for animation layer interfaces or layer-owning anim blueprints). */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static UObject* AddAnimLayerGraph(UBlueprint* Blueprint, FName LayerName);

	/** Compiles and returns "status=N errors=N warnings=N" followed by the log lines. */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static FString Compile(UBlueprint* Blueprint);

	/** Copy/paste text of every node in the graph (for inspection). */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static FString ExportGraph(UObject* Graph);

	/** One line per bone: "name|parent|tx ty tz|qx qy qz qw" (local ref pose). */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static TArray<FString> GetRefPose(USkeletalMesh* Mesh);

	/** Same for a skeleton asset. */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static TArray<FString> GetSkeletonRefPose(USkeleton* Skeleton);

	/** Sets the mesh's skeleton pointer (both must share bone names/parents) and marks it dirty. */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static bool SetMeshSkeleton(USkeletalMesh* Mesh, USkeleton* Skeleton);

	/** Adds or replaces a mesh-only socket. */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static bool SetMeshSocket(USkeletalMesh* Mesh, FName SocketName, FName BoneName, FVector Location, FRotator Rotation, FVector Scale);

	/** "name|vertices" of every morph target of the mesh. */
	UFUNCTION(BlueprintCallable, Category = "PalModTools")
	static TArray<FString> GetMorphTargets(USkeletalMesh* Mesh);
};
